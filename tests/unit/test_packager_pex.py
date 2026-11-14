from __future__ import annotations

from pathlib import Path

import pytest

from uv_bundler.domain.config import TargetConfig
from uv_bundler.services.packager import _pex_platform_tag, build_pex, build_pex_command
from uv_bundler.services.staging import StagingPaths


def make_staging(tmp_path: Path) -> StagingPaths:
    root = tmp_path / "staging"
    site = root / "site-packages"
    src = root / "src"
    for d in (site, src):
        d.mkdir(parents=True, exist_ok=True)
    (src / "app").mkdir()
    (src / "app" / "main.py").write_text("def run():\n    return 0\n")
    return StagingPaths(root=root, site_packages=site, sources=src)


# ── _pex_platform_tag ─────────────────────────────────────────────────────────


def test_pex_platform_tag_linux_x86_64_manylinux2014() -> None:
    tgt = TargetConfig(platform="linux", arch="x86_64", python_version="3.10", manylinux="2014")
    assert _pex_platform_tag(tgt) == "manylinux2014_x86_64-cp-310-cp310"


def test_pex_platform_tag_linux_aarch64_manylinux2014() -> None:
    tgt = TargetConfig(platform="linux", arch="aarch64", python_version="3.10", manylinux="2014")
    assert _pex_platform_tag(tgt) == "manylinux2014_aarch64-cp-310-cp310"


def test_pex_platform_tag_linux_manylinux2010() -> None:
    tgt = TargetConfig(platform="linux", arch="x86_64", python_version="3.10", manylinux="2010")
    assert _pex_platform_tag(tgt) == "manylinux2010_x86_64-cp-310-cp310"


def test_pex_platform_tag_linux_numeric_manylinux() -> None:
    tgt = TargetConfig(platform="linux", arch="x86_64", python_version="3.11", manylinux="31")
    tag = _pex_platform_tag(tgt)
    assert tag == "manylinux_2_31_x86_64-cp-311-cp311"


def test_pex_platform_tag_macos() -> None:
    tgt = TargetConfig(platform="macos", arch="x86_64", python_version="3.10")
    tag = _pex_platform_tag(tgt)
    assert tag == "macosx_10_9_x86_64-cp-310-cp310"


def test_pex_platform_tag_macos_apple_silicon() -> None:
    tgt = TargetConfig(platform="macos", arch="aarch64", python_version="3.12")
    assert _pex_platform_tag(tgt) == "macosx_11_0_arm64-cp-312-cp312"


def test_pex_platform_tag_windows() -> None:
    tgt = TargetConfig(platform="windows", arch="x86_64", python_version="3.10")
    assert _pex_platform_tag(tgt) == "win_amd64-cp-310-cp310"


def test_pex_platform_tag_defaults() -> None:
    # All None → linux/x86_64/3.12/manylinux2014
    tgt = TargetConfig()
    tag = _pex_platform_tag(tgt)
    assert tag == "manylinux2014_x86_64-cp-312-cp312"


# ── build_pex_command ─────────────────────────────────────────────────────────


def test_build_pex_command_uses_module_and_output(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"
    cmd = build_pex_command(paths, "app.main:run", out)
    assert cmd[0] == "pex"
    assert "-e" in cmd
    assert cmd[cmd.index("-e") + 1] == "app.main:run"
    assert "-o" in cmd
    assert Path(cmd[cmd.index("-o") + 1]) == out


def test_build_pex_command_with_lock_and_platform(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    lock = tmp_path / "resolved.lock"
    lock.write_text("pyspark==3.5.0\n")
    target = TargetConfig(platform="linux", arch="x86_64", python_version="3.10", manylinux="2014")
    out = tmp_path / "app.pex"
    cmd = build_pex_command(paths, "app.main:run", out, lock_file=lock, target=target)
    assert "-r" in cmd
    assert str(lock) in cmd
    assert "--platform" in cmd
    plat_val = cmd[cmd.index("--platform") + 1]
    assert "manylinux2014_x86_64" in plat_val
    assert "cp310" in plat_val and "cp-310" in plat_val


def test_build_pex_command_without_lock_or_target(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"
    cmd = build_pex_command(paths, "app.main:run", out)
    assert "-r" not in cmd
    assert "--platform" not in cmd


def test_build_pex_command_includes_tools_flag(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"
    cmd = build_pex_command(paths, "app.main:run", out)
    assert "--include-tools" in cmd


def test_build_pex_command_sources_directory(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"
    cmd = build_pex_command(paths, "app.main:run", out)
    assert "--sources-directory" in cmd
    assert str(paths.sources) in cmd


# ── build_pex ─────────────────────────────────────────────────────────────────


def test_build_pex_calls_runner_with_cwd(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"
    called: dict[str, object] = {}

    def fake_run(args: list[str], cwd: Path | None = None) -> int:
        called["args"] = args
        called["cwd"] = cwd
        return 0

    rc = build_pex(paths, "app.main:run", out, run=fake_run)
    assert rc == 0
    assert called["cwd"] == paths.root
    assert called["args"] is not None
    assert called["args"][0] == "pex"  # type: ignore[index]


def test_build_pex_propagates_runner_failure(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"

    rc = build_pex(paths, "app.main:run", out, run=lambda *a, **kw: 1)
    assert rc == 1


@pytest.mark.parametrize("lock_exists", [True, False])
def test_build_pex_lock_file_optional(tmp_path: Path, lock_exists: bool) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"
    lock = tmp_path / "resolved.lock"
    if lock_exists:
        lock.write_text("packaging==24.2\n")

    called: dict[str, object] = {}

    def fake_run(args: list[str], cwd: Path | None = None) -> int:
        called["args"] = args
        return 0

    build_pex(paths, "app.main:run", out, run=fake_run, lock_file=lock if lock_exists else None)
    assert called["args"] is not None
