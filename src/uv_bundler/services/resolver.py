from __future__ import annotations

from pathlib import Path
from typing import Protocol

from uv_bundler.domain.config import TargetConfig
from uv_bundler.domain.platforms import pep508_platform


class Runner(Protocol):
    def __call__(self, args: list[str], cwd: Path | None = None) -> int: ...


def build_compile_cmd(pyproject: Path, target: TargetConfig, lock_path: Path) -> list[str]:
    if not target.platform or not target.arch:
        raise ValueError("target requires platform and arch")
    platform = pep508_platform(target.platform, target.arch, target.manylinux)
    python_version = target.python_version or "3.10"
    return [
        "uv",
        "pip",
        "compile",
        str(pyproject),
        "--python-platform",
        platform,
        "--python-version",
        python_version,
        "--output-file",
        str(lock_path),
    ]


def compile_lockfile(
    pyproject: Path, target: TargetConfig, lock_path: Path, run: Runner, cwd: Path | None = None
) -> int:
    cmd = build_compile_cmd(pyproject, target, lock_path)
    return run(cmd, cwd=cwd)


def build_install_cmd(lock_path: Path, target: TargetConfig, site_packages: Path) -> list[str]:
    if not target.platform or not target.arch:
        raise ValueError("target requires platform and arch")
    platform = pep508_platform(target.platform, target.arch, target.manylinux)
    python_version = target.python_version or "3.10"
    return [
        "uv",
        "pip",
        "install",
        "-r",
        str(lock_path),
        "--target",
        str(site_packages),
        "--python-platform",
        platform,
        "--python-version",
        python_version,
    ]


def install_dependencies(
    lock_path: Path,
    target: TargetConfig,
    site_packages: Path,
    run: Runner,
    cwd: Path | None = None,
) -> int:
    cmd = build_install_cmd(lock_path, target, site_packages)
    return run(cmd, cwd=cwd)
