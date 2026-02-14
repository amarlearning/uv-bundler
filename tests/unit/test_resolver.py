from pathlib import Path

from uv_pack.domain.config import TargetConfig
from uv_pack.services.resolver import build_compile_cmd, compile_lockfile


def test_build_compile_cmd_linux() -> None:
    tgt = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="x86_64",
        python_version="3.10",
        manylinux="2014",
    )
    cmd = build_compile_cmd(Path("pyproject.toml"), tgt, Path(".uv-pack/resolved.lock"))
    assert cmd[:3] == ["uv", "pip", "compile"]
    assert "--python-platform" in cmd
    assert "x86_64-unknown-linux-gnu" in cmd
    assert "--python-version" in cmd
    assert "3.10" in cmd
    assert "--output-file" in cmd


def test_compile_lockfile_invokes_runner(tmp_path: Path) -> None:
    called = {}

    def fake_run(args: list[str], cwd: Path | None = None) -> int:
        called["args"] = args
        called["cwd"] = cwd
        return 0

    tgt = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="x86_64",
        python_version="3.10",
        manylinux="2014",
    )
    py = tmp_path / "pyproject.toml"
    py.write_text("[project]\nname='x'\n")
    out = tmp_path / "resolved.lock"
    code = compile_lockfile(py, tgt, out, fake_run, cwd=tmp_path)
    assert code == 0
    assert called["cwd"] == tmp_path
    assert called["args"][0] == "uv"
