from typing import Optional

from frontend.symbol.symbol import Symbol

from .scope import Scope


class ScopeStack:
    def __init__(self) -> None:
        self.scopes: list[Scope] = []

    def push(self, scope: Scope) -> None:
        self.scopes.append(scope)

    def pop(self) -> Scope:
        return self.scopes.pop()

    def declare(self, symbol: Symbol) -> None:
        self.scopes[-1].declare(symbol)

    def lookupCurrent(self, name: str) -> Optional[Symbol]:
        return self.scopes[-1].lookup(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            symbol = scope.lookup(name)
            if symbol is not None:
                return symbol
        return None
