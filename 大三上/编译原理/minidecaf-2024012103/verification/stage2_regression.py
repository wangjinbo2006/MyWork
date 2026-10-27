import argparse
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CC = ["riscv64-unknown-elf-gcc", "-std=c17", "-march=rv32im", "-mabi=ilp32"]

VALID = {
    "empty_function": "int main() {}",
    "empty_blocks": "int main() { ; {} { ; { ; } } return 7; }",
    "declare_then_assign": "int main() { int a; a = 42; return a; }",
    "initialization": "int main() { int a = 6; int b = a * 7; return b; }",
    "copy_then_mutate": "int main() { int a = 6; int b = a; a = 9; return b; }",
    "chain_assignment": "int main() { int a; int b; int c; a = b = c = 13; return a + b + c; }",
    "assignment_value": "int main() { int a; return 7 + (a = 9) * 3; }",
    "assignment_initializer": "int main() { int a; int b = (a = 7); return a + b; }",
    "return_assignment": "int main() { int a; int b = 17; return a = b; }",
    "self_assignment": "int main() { int a = 27; a = a; return a; }",
    "expression_statements": "int main() { 1 + 2; int a = 4; a; a = a + 3; return a; }",
    "shadow_restore": "int main() { int a = 2; { int a = 9; a = 10; } return a; }",
    "outer_write": "int main() { int a = 2; { a = 9; } return a; }",
    "late_shadow": "int main() { int a = 2; { a = 7; int a = 99; a = 13; } return a; }",
    "sibling_scopes": "int main() { int r = 0; { int a = 3; r = r + a; } { int a = 8; r = r + a; } return r; }",
    "late_outer_declaration": "int main() { { int a = 3; } int a = 11; return a; }",
    "nested_initializers": "int main() { int a = 3; { int b = a + 4; { int a = b + 5; return a; } } }",
    "three_shadow_levels": "int main() { int a = 3; int r = 0; { int a = 5; { int a = 7; r = a; } r = r + a; } return r + a; }",
    "nested_early_return": "int main() { int a = 42; { return a; } a = a + 1; return a; }",
    "unreachable_uninitialized": "int main() { return 17; int a; return a; }",
    "unreachable_division": "int main() { return 19; int a = 0; a = 1 / a; return a; }",
    "implicit_return": "int main() { int a = 3; { a = 4; } }",
    "identifier_names": "int main() { int _a1 = 6; int a_2 = 7; int main = 8; return _a1 + a_2 + main; }",
    "signed_arithmetic": "int main() { int a = -37; int b = 6; return a / b * 10 + a % b; }",
    "comparisons_logic": "int main() { int a = -2; int b = 3; return (a < b) + (a <= b) + (b > a) + (b >= a) + (a != b) + (a == b) + (a && b) + (a || b) + !a + ~b; }",
    "full_width_result": "int main() { int a = 123456789; int b = 987654321; return a + b; }",
}

INVALID = {
    "duplicate": ("int main() { int a; int a; return 0; }", "declaration conflict"),
    "duplicate_initialized": ("int main() { int a = 1; int a = 2; return a; }", "declaration conflict"),
    "duplicate_inner": ("int main() { { int a; int a; } return 0; }", "declaration conflict"),
    "duplicate_after_block": ("int main() { int a; {} int a; return 0; }", "declaration conflict"),
    "undefined_read": ("int main() { return missing; }", "undefined variable"),
    "undefined_write": ("int main() { missing = 1; return 0; }", "undefined variable"),
    "use_before_declaration": ("int main() { a = 3; int a; return a; }", "undefined variable"),
    "initializer_before_declaration": ("int main() { int a = b; int b = 3; return a; }", "undefined variable"),
    "out_of_scope": ("int main() { { int a = 1; } return a; }", "undefined variable"),
    "sibling_scope_leak": ("int main() { { int a = 1; } { return a; } }", "undefined variable"),
    "inner_use_before_declaration": ("int main() { { a = 1; int a; } return 0; }", "undefined variable"),
    "undefined_after_return": ("int main() { return 0; missing = 1; }", "undefined variable"),
    "duplicate_after_return": ("int main() { int a; return 0; int a; }", "declaration conflict"),
    "literal_lvalue": ("int main() { 1 = 2; return 0; }", "Syntax error"),
    "expression_lvalue": ("int main() { int a = 1; a + 1 = 2; return a; }", "Syntax error"),
    "missing_semicolon": ("int main() { int a = 2 return a; }", "Syntax error"),
    "missing_brace": ("int main() { { return 0; }", "Syntax error"),
    "bad_integer_initializer": ("int main() { int a = 2147483648; return a; }", "bad integer value"),
}


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, **kwargs)
    if result.returncode:
        raise AssertionError(f"Command failed ({result.returncode}): {command}\n{result.stdout}{result.stderr}")
    return result.stdout


def generated_program(seed):
    rng = random.Random(seed)
    lines = ["int main() {", "int a = 11; int b = 23; int c = 37;"]
    scopes = [{"a", "b", "c"}]
    names = ["a", "b", "c", "d", "x", "y", "z", "v"]

    def expression():
        visible = sorted(set().union(*scopes))
        lhs = rng.choice(visible)
        rhs = rng.choice(visible + [str(rng.randrange(1, 100))])
        op = rng.choice(["+", "-", "*", "<", "<=", ">", ">=", "==", "!=", "&&", "||", "/", "%"])
        if op in ("/", "%"):
            rhs = f"(({rhs}) * ({rhs}) + 1)"
        return f"(({lhs} {op} {rhs}) % 127)"

    for _ in range(50):
        choice = rng.random()
        available = [name for name in names if name not in scopes[-1]]
        if choice < 0.16 and len(scopes) < 5:
            lines.append("{")
            scopes.append(set())
        elif choice < 0.30 and len(scopes) > 1:
            lines.append("}")
            scopes.pop()
        elif choice < 0.50 and available:
            name = rng.choice(available)
            lines.append(f"int {name} = {rng.randrange(-100, 101)};")
            scopes[-1].add(name)
        else:
            target = rng.choice(sorted(set().union(*scopes)))
            lines.append(f"{target} = {expression()};")
    lines.extend("}" for _ in scopes[1:])
    lines.append("return a * 10000 + b * 100 + c; }")
    return "\n".join(lines)


def pressure_program(count):
    declarations = "\n".join(f"int v{i} = {i + 1};" for i in range(count))
    total = " + ".join(f"v{i}" for i in range(count))
    return f"int main() {{ {declarations} int r = {total}; v0 = r; return v0 + v{count - 1}; }}"


def check_cfg():
    sys.path.insert(0, str(ROOT))
    from backend.dataflow.basicblock import BasicBlock, BlockKind
    from backend.dataflow.cfg import CFG

    nodes = [BasicBlock(BlockKind.CONTINUOUS, i, None, []) for i in range(6)]
    graph = CFG(nodes, [(0, 1), (0, 2), (1, 3), (3, 1), (4, 5), (5, 4)])
    assert {i for i in range(6) if graph.isReachable(i)} == {0, 1, 2, 3}
    assert not CFG([], []).isReachable(0)


def check_valid(directory, name, source, harness):
    cfile = directory / f"{name}.c"
    cfile.write_text(source)
    assembly = run([sys.executable, str(ROOT / "main.py"), "--input", str(cfile), "--riscv"], cwd=ROOT)
    asmfile = cfile.with_suffix(".s")
    asmfile.write_text(re.sub(r"\bmain\b", "minidecaf_main", assembly))
    reference_source = directory / f"{name}_reference.c"
    body, trailing = source.rsplit("}", 1)
    reference_source.write_text(body + "return 0; }" + trailing)
    reference = cfile.with_suffix(".o")
    run(CC + ["-Dmain=reference_main", "-c", str(reference_source), "-o", str(reference)])
    executable = cfile.with_suffix(".elf")
    run(CC + [str(harness), str(reference), str(asmfile), "-o", str(executable)])
    run(["qemu-riscv32", str(executable)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--random-cases", type=int, default=100)
    args = parser.parse_args()
    check_cfg()
    cases = dict(VALID)
    for count in (32, 80, 256):
        cases[f"register_pressure_{count}"] = pressure_program(count)
    for seed in range(args.random_cases):
        cases[f"generated_{seed:03d}"] = generated_program(seed)

    directory = Path(tempfile.mkdtemp(prefix="minidecaf-stage2-"))
    harness = directory / "harness.c"
    harness.write_text("#include <stdio.h>\nint reference_main(void); int minidecaf_main(void);\n"
                       "int main(void) { int expected = reference_main(); int actual = minidecaf_main(); "
                       "if (expected != actual) { printf(\"expected=%d actual=%d\\n\", expected, actual); return 1; } return 0; }\n")
    try:
        for index, (name, source) in enumerate(cases.items(), 1):
            check_valid(directory, name, source, harness)
            if index % 25 == 0 or index == len(cases):
                print(f"Valid programs: {index}/{len(cases)} passed", flush=True)
        for name, (source, diagnostic) in INVALID.items():
            cfile = directory / f"{name}.c"
            cfile.write_text(source)
            result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--input", str(cfile), "--riscv"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=20)
            assert result.returncode != 0 and diagnostic in result.stderr, (name, result.stdout, result.stderr)
        print(f"Invalid programs: {len(INVALID)}/{len(INVALID)} correctly rejected")
        print("CFG reachability: branch, reachable cycle, disconnected cycle, empty graph passed")
        print(f"PASS: {len(cases)} full-width GCC comparisons, {len(INVALID)} diagnostics, CFG checks")
    except Exception:
        print(f"Failure artifacts retained in {directory}", file=sys.stderr)
        raise
    else:
        import shutil
        shutil.rmtree(directory)


if __name__ == "__main__":
    main()
