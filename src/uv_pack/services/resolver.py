from __future__ import annotations

from pathlib import Path
from typing import Protocol

from uv_pack.domain.config import TargetConfig
from uv_pack.domain.platforms import pep508_platform


class Runner(Protocol):
    def __call__(self, args: list[str], cwd: Path | None = None) -> int: ...


def build_compile_cmd(pyproject: Path, target: TargetConfig, lock_path: Path) -> list[str]:
    if not target.platform or not target.arch or not target.python_version:
        raise ValueError("target requires platform, arch, and python_version")
    platform = pep508_platform(target.platform, target.arch)
    return [
        "uv",
        "pip",
        "compile",
        str(pyproject),
        "--python-platform",
        platform,
        "--python-version",
        str(target.python_version),
        "--output-file",
        str(lock_path),
    ]


def compile_lockfile(
    pyproject: Path, target: TargetConfig, lock_path: Path, run: Runner, cwd: Path | None = None
) -> int:
    cmd = build_compile_cmd(pyproject, target, lock_path)
    return run(cmd, cwd=cwd)
