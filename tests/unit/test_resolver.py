from pathlib import Path

from uv_pack.domain.config import TargetConfig
from uv_pack.services.resolver import build_compile_cmd, compile_lockfile


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.last_cwd: Path | None = None

    def __call__(self, args: list[str], cwd: Path | None = None) -> int:
        self.calls.append(list(args))
        self.last_cwd = cwd
        return 0


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
    assert "x86_64-manylinux2014" in cmd
    assert "--python-version" in cmd
    assert "3.10" in cmd
    assert "--output-file" in cmd


def test_compile_lockfile_invokes_runner(tmp_path: Path) -> None:
    runner = FakeRunner()

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
    code = compile_lockfile(py, tgt, out, runner, cwd=tmp_path)
    assert code == 0
    assert runner.last_cwd == tmp_path
    assert runner.calls[0][0] == "uv"
