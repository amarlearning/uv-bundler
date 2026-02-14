import shutil
import textwrap
from pathlib import Path

import pytest

from uv_pack.adapters import process
from uv_pack.domain.config import TargetConfig
from uv_pack.services.resolver import compile_lockfile

has_uv = shutil.which("uv") is not None
requires_uv = pytest.mark.skipif(not has_uv, reason="uv not found on PATH")


@requires_uv
@pytest.mark.parametrize(
    "platform,arch,pyver",
    [
        ("linux", "x86_64", "3.10"),
        ("linux", "aarch64", "3.10"),
    ],
)
def test_compile_lockfile_cross_platform(
    tmp_path: Path, platform: str, arch: str, pyver: str
) -> None:
    pyproject = textwrap.dedent("""
        [project]
        name = "it-sample"
        version = "0.0.0"
        dependencies = ["packaging==24.2"]
        """).strip()
    (tmp_path / "pyproject.toml").write_text(pyproject)

    tgt = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform=platform,
        arch=arch,
        python_version=pyver,
        manylinux="2014",
    )
    out = tmp_path / ".uv-pack" / f"resolved-{platform}-{arch}.lock"
    out.parent.mkdir(parents=True, exist_ok=True)
    code = compile_lockfile(tmp_path / "pyproject.toml", tgt, out, run=process.run, cwd=tmp_path)
    assert code == 0
    assert out.exists()
    assert out.stat().st_size > 0
