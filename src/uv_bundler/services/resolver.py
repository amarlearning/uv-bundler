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


def _pip_platform_tag(target: TargetConfig) -> str:
    """Return the pip ``--platform`` wheel tag for cross-platform downloads.

    e.g. ``manylinux2014_x86_64`` or ``manylinux_2_31_x86_64``
    """
    arch = (target.arch or "x86_64").lower()
    plat = (target.platform or "linux").lower()
    if plat == "linux":
        ml = target.manylinux or "2014"
        if ml in ("2010", "2014"):
            return f"manylinux{ml}_{arch}"
        return f"manylinux_2_{ml}_{arch}"
    if plat == "macos":
        return f"macosx_10_9_{arch}"
    return f"{plat}_{arch}"


def build_pip_download_cmd(lock_path: Path, target: TargetConfig, wheels_dir: Path) -> list[str]:
    """Build a ``pip download`` command for cross-platform wheel pre-fetching.

    Uses standard pip (not uv) because pip supports ``--platform``, ``--abi``,
    and ``--only-binary`` for cross-platform downloads.  The downloaded wheels
    are later fed to pex via ``--find-links`` so pex never needs the network.
    """
    if not target.platform or not target.arch:
        raise ValueError("target requires platform and arch")
    platform_tag = _pip_platform_tag(target)
    python_version = (target.python_version or "3.10").replace(".", "")
    abi = f"cp{python_version}"
    return [
        "pip",
        "download",
        "-r",
        str(lock_path),
        "--dest",
        str(wheels_dir),
        "--platform",
        platform_tag,
        "--python-version",
        python_version,
        "--abi",
        abi,
        "--implementation",
        "cp",
        "--only-binary",
        ":all:",
    ]


def download_wheels(
    lock_path: Path,
    target: TargetConfig,
    wheels_dir: Path,
    run: Runner,
    cwd: Path | None = None,
) -> int:
    """Download target-platform wheels using pip for offline PEX assembly."""
    cmd = build_pip_download_cmd(lock_path, target, wheels_dir)
    return run(cmd, cwd=cwd)
