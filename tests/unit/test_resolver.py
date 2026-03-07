from __future__ import annotations

from pathlib import Path

import pytest

from uv_pack.domain.config import TargetConfig
from uv_pack.services.resolver import (
    _pip_platform_tag,
    build_compile_cmd,
    build_install_cmd,
    build_pip_download_cmd,
    compile_lockfile,
    download_wheels,
    install_dependencies,
)


class FakeRunner:
    def __init__(self, return_code: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.last_cwd: Path | None = None
        self._rc = return_code

    def __call__(self, args: list[str], cwd: Path | None = None) -> int:
        self.calls.append(list(args))
        self.last_cwd = cwd
        return self._rc


def _linux_target(**overrides: object) -> TargetConfig:
    defaults = dict(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="x86_64",
        python_version="3.10",
        manylinux="2014",
    )
    defaults.update(overrides)
    return TargetConfig(**defaults)  # type: ignore[arg-type]


# ── build_compile_cmd ─────────────────────────────────────────────────────────


def test_build_compile_cmd_linux() -> None:
    tgt = _linux_target()
    cmd = build_compile_cmd(Path("pyproject.toml"), tgt, Path(".uv-pack/resolved.lock"))
    assert cmd[:3] == ["uv", "pip", "compile"]
    assert "--python-platform" in cmd
    assert "x86_64-manylinux2014" in cmd
    assert "--python-version" in cmd
    assert "3.10" in cmd
    assert "--output-file" in cmd


def test_build_compile_cmd_aarch64() -> None:
    tgt = _linux_target(arch="aarch64")
    cmd = build_compile_cmd(Path("pyproject.toml"), tgt, Path("resolved.lock"))
    assert "aarch64-manylinux2014" in cmd


def test_build_compile_cmd_missing_platform_raises() -> None:
    tgt = TargetConfig(format="jar", entry_point="app.main:run")
    with pytest.raises(ValueError):
        build_compile_cmd(Path("pyproject.toml"), tgt, Path("resolved.lock"))


def test_build_compile_cmd_defaults_python_version() -> None:
    tgt = _linux_target(python_version=None)
    cmd = build_compile_cmd(Path("pyproject.toml"), tgt, Path("resolved.lock"))
    assert "3.10" in cmd


# ── compile_lockfile ──────────────────────────────────────────────────────────


def test_compile_lockfile_invokes_runner(tmp_path: Path) -> None:
    runner = FakeRunner()
    tgt = _linux_target()
    py = tmp_path / "pyproject.toml"
    py.write_text("[project]\nname='x'\n")
    out = tmp_path / "resolved.lock"
    code = compile_lockfile(py, tgt, out, runner, cwd=tmp_path)
    assert code == 0
    assert runner.last_cwd == tmp_path
    assert runner.calls[0][0] == "uv"


def test_compile_lockfile_propagates_runner_failure(tmp_path: Path) -> None:
    runner = FakeRunner(return_code=1)
    tgt = _linux_target()
    py = tmp_path / "pyproject.toml"
    py.write_text("")
    code = compile_lockfile(py, tgt, tmp_path / "out.lock", runner)
    assert code == 1


# ── build_install_cmd ─────────────────────────────────────────────────────────


def test_build_install_cmd_structure() -> None:
    tgt = _linux_target()
    lock = Path(".uv-pack/resolved.lock")
    site = Path(".uv-pack/staging/site-packages")
    cmd = build_install_cmd(lock, tgt, site)
    assert cmd[:3] == ["uv", "pip", "install"]
    assert "-r" in cmd
    assert str(lock) in cmd
    assert "--target" in cmd
    assert str(site) in cmd
    assert "--python-platform" in cmd
    assert "x86_64-manylinux2014" in cmd
    assert "--python-version" in cmd
    assert "3.10" in cmd


def test_build_install_cmd_missing_platform_raises() -> None:
    tgt = TargetConfig(format="jar", entry_point="app.main:run")
    with pytest.raises(ValueError):
        build_install_cmd(Path("resolved.lock"), tgt, Path("site-packages"))


def test_build_install_cmd_defaults_python_version() -> None:
    tgt = _linux_target(python_version=None)
    cmd = build_install_cmd(Path("lock"), tgt, Path("site"))
    assert "3.10" in cmd


# ── install_dependencies ──────────────────────────────────────────────────────


def test_install_dependencies_invokes_runner(tmp_path: Path) -> None:
    runner = FakeRunner()
    tgt = _linux_target()
    lock = tmp_path / "resolved.lock"
    lock.write_text("packaging==24.2\n")
    site = tmp_path / "site-packages"
    code = install_dependencies(lock, tgt, site, runner, cwd=tmp_path)
    assert code == 0
    assert runner.last_cwd == tmp_path
    assert runner.calls[0][:3] == ["uv", "pip", "install"]


def test_install_dependencies_propagates_runner_failure(tmp_path: Path) -> None:
    rc = 2
    runner = FakeRunner(return_code=rc)
    tgt = _linux_target()
    lock = tmp_path / "resolved.lock"
    lock.write_text("")
    code = install_dependencies(lock, tgt, tmp_path / "site", runner)
    assert code == rc


# ── _pip_platform_tag ─────────────────────────────────────────────────────────


def test_pip_platform_tag_linux_manylinux2014() -> None:
    tgt = _linux_target(arch="x86_64", manylinux="2014")
    assert _pip_platform_tag(tgt) == "manylinux2014_x86_64"


def test_pip_platform_tag_linux_manylinux2010() -> None:
    tgt = _linux_target(arch="aarch64", manylinux="2010")
    assert _pip_platform_tag(tgt) == "manylinux2010_aarch64"


def test_pip_platform_tag_linux_numeric_manylinux() -> None:
    tgt = _linux_target(arch="x86_64", manylinux="31")
    assert _pip_platform_tag(tgt) == "manylinux_2_31_x86_64"


def test_pip_platform_tag_macos() -> None:
    tgt = TargetConfig(platform="macos", arch="x86_64")
    assert _pip_platform_tag(tgt) == "macosx_10_9_x86_64"


def test_pip_platform_tag_unknown_platform() -> None:
    tgt = TargetConfig(platform="windows", arch="x86_64")
    assert _pip_platform_tag(tgt) == "windows_x86_64"


def test_pip_platform_tag_defaults() -> None:
    # No platform/arch set — defaults to linux/x86_64/2014
    tgt = TargetConfig()
    assert _pip_platform_tag(tgt) == "manylinux2014_x86_64"


# ── build_pip_download_cmd ────────────────────────────────────────────────────


def test_build_pip_download_cmd_structure(tmp_path: Path) -> None:
    tgt = _linux_target()
    lock = tmp_path / "resolved.lock"
    dest = tmp_path / "wheels"
    cmd = build_pip_download_cmd(lock, tgt, dest)
    assert cmd[0] == "pip"
    assert "download" in cmd
    assert "-r" in cmd
    assert str(lock) in cmd
    assert "--dest" in cmd
    assert str(dest) in cmd
    assert "--platform" in cmd
    assert "manylinux2014_x86_64" in cmd
    assert "--python-version" in cmd
    assert "310" in cmd
    assert "--abi" in cmd
    assert "cp310" in cmd
    assert "--only-binary" in cmd
    assert ":all:" in cmd


def test_build_pip_download_cmd_missing_platform_raises(tmp_path: Path) -> None:
    tgt = TargetConfig(format="jar", entry_point="app.main:run")
    with pytest.raises(ValueError):
        build_pip_download_cmd(tmp_path / "lock", tgt, tmp_path / "wheels")


# ── download_wheels ───────────────────────────────────────────────────────────


def test_download_wheels_invokes_runner(tmp_path: Path) -> None:
    runner = FakeRunner()
    tgt = _linux_target()
    lock = tmp_path / "resolved.lock"
    lock.write_text("packaging==24.2\n")
    wheels = tmp_path / "wheels"
    code = download_wheels(lock, tgt, wheels, runner, cwd=tmp_path)
    assert code == 0
    assert runner.last_cwd == tmp_path
    assert runner.calls[0][0] == "pip"
    assert "download" in runner.calls[0]
