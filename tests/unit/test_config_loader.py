import textwrap
from pathlib import Path

from uv_pack.services.config_loader import load_pyproject, merge_overrides


def write_pyproject(tmp_path: Path) -> Path:
    content = textwrap.dedent("""
        [tool.uv-pack]
        project_name = "demo"
        default_target = "spark-prod"
        output_base = "./dist"

        [tool.uv-pack.targets.spark-prod]
        format = "jar"
        entry_point = "app.main:run"
        platform = "linux"
        arch = "x86_64"
        python_version = "3.10"
        manylinux = "2014"
        """).strip()
    path = tmp_path / "pyproject.toml"
    path.write_text(content)
    return path


def test_load_pyproject_parses_config(tmp_path: Path) -> None:
    path = write_pyproject(tmp_path)
    cfg = load_pyproject(path)
    tgt = cfg.resolve_target("spark-prod")
    assert tgt.format == "jar"
    assert tgt.entry_point == "app.main:run"
    assert tgt.platform == "linux"
    assert tgt.arch == "x86_64"
    assert tgt.python_version == "3.10"
    assert tgt.manylinux == "2014"


def test_merge_overrides_is_immutable(tmp_path: Path) -> None:
    path = write_pyproject(tmp_path)
    cfg = load_pyproject(path)
    base = cfg.resolve_target("spark-prod")
    updated = merge_overrides(base, {"arch": "aarch64", "platform": "linux"})
    assert updated.arch == "aarch64"
    assert updated.platform == "linux"
    # original remains unchanged
    assert base.arch == "x86_64"
