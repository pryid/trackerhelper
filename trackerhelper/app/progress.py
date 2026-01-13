from __future__ import annotations

from typing import Protocol


class ProgressCallback(Protocol):
    def start(self, total: int) -> None: ...

    def advance(self, step: int = 1) -> None: ...

    def finish(self) -> None: ...


class NullProgress:
    def start(self, total: int) -> None:
        return None

    def advance(self, step: int = 1) -> None:
        return None

    def finish(self) -> None:
        return None
