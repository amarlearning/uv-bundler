from __future__ import annotations

from pathlib import Path

from uv_pack.domain.config import TargetConfig
from uv_pack.services.packager import build_pex, build_pex_command
from uv_pack.services.staging import StagingPaths


def make_staging(tmp_path: Path) -> StagingPaths:
    root = tmp_path / "staging"
    site = root / "site-packages"
    src = root / "src"
    for d in (site, src):
        d.mkdir(parents=True, exist_ok=True)
    (src / "app").mkdir()
    (src / "app" / "main.py").write_text("def run():\n    return 0\n")
    return StagingPaths(root=root, site_packages=site, sources=src)


def test_build_pex_command_uses_module_and_output(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"
    cmd = build_pex_command(paths, "app.main:run", out)
    assert "pex" == cmd[0]
    # ensure module appears
    assert "-e" in cmd
    m_index = cmd.index("-e")
    assert cmd[m_index + 1] == "app.main:run"
    # ensure output flag and path
    assert "-o" in cmd
    o_index = cmd.index("-o")
    assert Path(cmd[o_index + 1]) == out


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
    plat_idx = cmd.index("--platform")
    assert "manylinux2014_x86_64" in cmd[plat_idx + 1]
    assert "cp310" in cmd[plat_idx + 1] and "cp-310" in cmd[plat_idx + 1]


def test_build_pex_calls_runner_with_cwd(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "app.pex"

    called = {"args": None, "cwd": None}

    def fake_run(args: list[str], cwd: Path | None = None) -> int:
        called["args"] = args
        called["cwd"] = cwd
        return 0

    rc = build_pex(paths, "app.main:run", out, run=fake_run)
    assert rc == 0
    assert called["cwd"] == paths.root
    assert called["args"] is not None
    assert called["args"][0] == "pex"
