from __future__ import annotations

from pathlib import Path

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
    assert "-m" in cmd
    m_index = cmd.index("-m")
    assert cmd[m_index + 1] == "app.main"
    # ensure output flag and path
    assert "-o" in cmd
    o_index = cmd.index("-o")
    assert Path(cmd[o_index + 1]) == out


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
