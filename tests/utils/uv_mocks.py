from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FakeRunner:
    code: int = 0
    calls: list[list[str]] = field(default_factory=list)
    last_cwd: Path | None = None

    def __call__(self, args: list[str], cwd: Path | None = None) -> int:
        self.calls.append(list(args))
        self.last_cwd = cwd
        return self.code


def runner_with_behavior(predicate: Callable[[list[str]], bool], code: int = 1) -> FakeRunner:
    fr = FakeRunner(code=0)

    def _call(args: list[str], cwd: Path | None = None) -> int:
        fr.calls.append(list(args))
        fr.last_cwd = cwd
        if predicate(args):
            return code
        return 0

    # type: ignore[method-assign]
    fr.__call__ = _call  # replace call behavior for tests
    return fr
