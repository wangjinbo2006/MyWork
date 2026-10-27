from frontend.ast.tree import *
from frontend.ast.visitor import Visitor
from frontend.scope.scope import Scope, ScopeKind
from frontend.scope.scopestack import ScopeStack
from frontend.symbol.varsymbol import VarSymbol
from utils.error import *
from utils.riscv import MAX_INT


class Namer(Visitor[ScopeStack, None]):
    def transform(self, program: Program) -> Program:
        program.globalScope = Scope(ScopeKind.GLOBAL)
        ctx = ScopeStack()
        ctx.push(program.globalScope)
        try:
            program.accept(self, ctx)
        finally:
            ctx.pop()
        return program

    def visitProgram(self, program: Program, ctx: ScopeStack) -> None:
        if not program.hasMainFunc():
            raise DecafNoMainFuncError

        for func in program.functions().values():
            func.accept(self, ctx)

    def visitFunction(self, func: Function, ctx: ScopeStack) -> None:
        func.body.accept(self, ctx)

    def visitBlock(self, block: Block, ctx: ScopeStack) -> None:
        scope = Scope(ScopeKind.LOCAL)
        block.setattr("scope", scope)
        ctx.push(scope)
        try:
            for child in block:
                child.accept(self, ctx)
        finally:
            ctx.pop()

    def visitReturn(self, stmt: Return, ctx: ScopeStack) -> None:
        stmt.expr.accept(self, ctx)

    def visitIf(self, stmt: If, ctx: ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        stmt.then.accept(self, ctx)

        if not stmt.otherwise is NULL:
            stmt.otherwise.accept(self, ctx)

    def visitWhile(self, stmt: While, ctx: ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        stmt.body.accept(self, ctx)

    def visitBreak(self, stmt: Break, ctx: ScopeStack) -> None:
        raise NotImplementedError

    def visitDeclaration(self, decl: Declaration, ctx: ScopeStack) -> None:
        name = decl.ident.value
        if ctx.lookupCurrent(name) is not None:
            raise DecafDeclConflictError(name)

        symbol = VarSymbol(name, decl.var_t.type)
        ctx.declare(symbol)
        decl.setattr("symbol", symbol)
        decl.ident.setattr("symbol", symbol)
        if decl.init_expr is not NULL:
            decl.init_expr.accept(self, ctx)

    def visitAssignment(self, expr: Assignment, ctx: ScopeStack) -> None:
        self.visitBinary(expr, ctx)

    def visitUnary(self, expr: Unary, ctx: ScopeStack) -> None:
        expr.operand.accept(self, ctx)

    def visitBinary(self, expr: Binary, ctx: ScopeStack) -> None:
        expr.lhs.accept(self, ctx)
        expr.rhs.accept(self, ctx)

    def visitCondExpr(self, expr: ConditionExpression, ctx: ScopeStack) -> None:
        raise NotImplementedError

    def visitIdentifier(self, ident: Identifier, ctx: ScopeStack) -> None:
        symbol = ctx.lookup(ident.value)
        if symbol is None:
            raise DecafUndefinedVarError(ident.value)
        ident.setattr("symbol", symbol)

    def visitIntLiteral(self, expr: IntLiteral, ctx: ScopeStack) -> None:
        value = expr.value
        if value > MAX_INT:
            raise DecafBadIntValueError(value)
