import shutil
import textwrap
from pathlib import Path

import pytest

from uv_pack.adapters import process
from uv_pack.domain.config import TargetConfig
from uv_pack.services.resolver import compile_lockfile

has_uv = shutil.which("uv") is not None
requires_uv = pytest.mark.skipif(not has_uv, reason="uv not found on PATH")


def _write_min_pyproject(tmp: Path, extra_deps: list[str] | None = None) -> Path:
    deps = ['"packaging==24.2"'] + [f'"{d}"' for d in (extra_deps or [])]
    deps_str = ", ".join(deps)
    pyproject = textwrap.dedent(
        f"""
        [project]
        name = "it-sample"
        version = "0.0.0"
        dependencies = [{deps_str}]
        """
    ).strip()
    p = tmp / "pyproject.toml"
    p.write_text(pyproject)
    return p


@requires_uv
@pytest.mark.parametrize(
    "platform,arch,pyver",
    [
        ("linux", "x86_64", "3.10"),
        ("linux", "x86_64", "3.11"),
        ("linux", "x86_64", "3.12"),
        ("linux", "x86_64", "3.13"),
        ("linux", "aarch64", "3.10"),
    ],
)
def test_compile_lockfile_cross_platform_matrix(
    tmp_path: Path, platform: str, arch: str, pyver: str
) -> None:
    py = _write_min_pyproject(tmp_path)
    tgt = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform=platform,
        arch=arch,
        python_version=pyver,
        manylinux="2014",
    )
    out = tmp_path / ".uv-pack" / f"resolved-{platform}-{arch}-{pyver}.lock"
    out.parent.mkdir(parents=True, exist_ok=True)
    code = compile_lockfile(py, tgt, out, run=process.run, cwd=tmp_path)
    assert code == 0
    assert out.exists()
    data = out.read_text()
    assert "packaging==24.2" in data
    assert "uv pip compile" in data


def test_invalid_combo_raises_value_error(tmp_path: Path) -> None:
    py = _write_min_pyproject(tmp_path)
    tgt = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="mips",
        python_version="3.10",
        manylinux="2014",
    )
    with pytest.raises(ValueError):
        compile_lockfile(py, tgt, tmp_path / "x.lock", run=process.run, cwd=tmp_path)


@requires_uv
def test_missing_python_version_defaults_to_3_10(tmp_path: Path) -> None:
    # python_version=None is accepted; the resolver defaults to "3.10"
    py = _write_min_pyproject(tmp_path)
    tgt = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="x86_64",
        python_version=None,
        manylinux="2014",
    )
    out = tmp_path / "x.lock"
    code = compile_lockfile(py, tgt, out, run=process.run, cwd=tmp_path)
    assert code == 0
    assert out.exists()


@requires_uv
def test_compile_lockfile_is_repeatable(tmp_path: Path) -> None:
    py = _write_min_pyproject(tmp_path, extra_deps=["attrs==24.2.0"])
    tgt = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="x86_64",
        python_version="3.10",
        manylinux="2014",
    )
    out = tmp_path / ".uv-pack" / "resolved.lock"
    out.parent.mkdir(parents=True, exist_ok=True)
    code1 = compile_lockfile(py, tgt, out, run=process.run, cwd=tmp_path)
    data1 = out.read_text()
    code2 = compile_lockfile(py, tgt, out, run=process.run, cwd=tmp_path)
    data2 = out.read_text()
    assert code1 == 0 and code2 == 0
    assert "packaging==24.2" in data1 and "attrs==24.2.0" in data1
    assert data2 == data1
