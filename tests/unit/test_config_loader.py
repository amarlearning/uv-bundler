import textwrap
from pathlib import Path

import pytest
from pydantic import ValidationError

from uv_bundler.services import config_loader
from uv_bundler.services.config_loader import load_pyproject, merge_overrides


def write_pyproject(tmp_path: Path, content: str | None = None) -> Path:
    if content is None:
        content = textwrap.dedent(
            """
            [tool.uv-bundler]
            project_name = "demo"
            default_target = "spark-prod"
            output_base = "./dist"

            [tool.uv-bundler.targets.spark-prod]
            format = "jar"
            entry_point = "app.main:run"
            platform = "linux"
            arch = "x86_64"
            python_version = "3.10"
            manylinux = "2014"
            """
        ).strip()
    path = tmp_path / "pyproject.toml"
    path.write_text(content)
    return path


# ── load_pyproject ────────────────────────────────────────────────────────────


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


def test_load_pyproject_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.toml"
    with pytest.raises(FileNotFoundError):
        load_pyproject(missing)


def test_load_pyproject_wraps_pydantic_validation_errors(tmp_path: Path, monkeypatch) -> None:
    def failing_uv_bundler_config(*args, **kwargs):
        raise ValidationError.from_exception_data("UvBundlerConfig", [])

    monkeypatch.setattr(config_loader, "UvBundlerConfig", failing_uv_bundler_config)
    path = write_pyproject(tmp_path)
    with pytest.raises(ValueError) as exc:
        load_pyproject(path)
    assert "Invalid uv-bundler configuration" in str(exc.value)


def test_load_pyproject_with_multiple_targets(tmp_path: Path) -> None:
    content = textwrap.dedent(
        """
        [tool.uv-bundler]
        default_target = "spark-jar"

        [tool.uv-bundler.targets.spark-jar]
        format = "jar"
        entry_point = "app.main:run"
        platform = "linux"
        arch = "x86_64"

        [tool.uv-bundler.targets.spark-pex]
        format = "pex"
        entry_point = "app.main:run"
        platform = "linux"
        arch = "aarch64"
        """
    ).strip()
    path = write_pyproject(tmp_path, content)
    cfg = load_pyproject(path)
    jar = cfg.resolve_target("spark-jar")
    pex = cfg.resolve_target("spark-pex")
    assert jar.format == "jar"
    assert jar.arch == "x86_64"
    assert pex.format == "pex"
    assert pex.arch == "aarch64"


def test_load_pyproject_global_config_fields(tmp_path: Path) -> None:
    path = write_pyproject(tmp_path)
    cfg = load_pyproject(path)
    assert cfg.global_config.project_name == "demo"
    assert cfg.global_config.default_target == "spark-prod"
    assert cfg.global_config.output_base == "./dist"


def test_load_pyproject_missing_uv_bundler_section_returns_empty_config(tmp_path: Path) -> None:
    """A pyproject.toml without [tool.uv-bundler] should produce an empty config."""
    content = "[project]\nname = 'x'\nversion = '0.1.0'\n"
    path = write_pyproject(tmp_path, content)
    cfg = load_pyproject(path)
    assert cfg.global_config.default_target is None
    assert cfg.targets == {}


# ── merge_overrides ───────────────────────────────────────────────────────────


def test_merge_overrides_is_immutable(tmp_path: Path) -> None:
    path = write_pyproject(tmp_path)
    cfg = load_pyproject(path)
    base = cfg.resolve_target("spark-prod")
    updated = merge_overrides(base, {"arch": "aarch64", "platform": "linux"})
    assert updated.arch == "aarch64"
    assert updated.platform == "linux"
    # original remains unchanged
    assert base.arch == "x86_64"


def test_merge_overrides_none_values_ignored(tmp_path: Path) -> None:
    """None values in overrides dict must not overwrite existing config values."""
    path = write_pyproject(tmp_path)
    cfg = load_pyproject(path)
    base = cfg.resolve_target("spark-prod")
    updated = merge_overrides(base, {"arch": None, "python_version": None, "manylinux": None})
    assert updated.arch == "x86_64"
    assert updated.python_version == "3.10"
    assert updated.manylinux == "2014"


def test_merge_overrides_partial_fields(tmp_path: Path) -> None:
    path = write_pyproject(tmp_path)
    cfg = load_pyproject(path)
    base = cfg.resolve_target("spark-prod")
    updated = merge_overrides(base, {"arch": "aarch64"})
    assert updated.arch == "aarch64"
    assert updated.python_version == "3.10"  # unchanged
    assert updated.platform == "linux"  # unchanged


# ── slim / slim_exclude parsing ───────────────────────────────────────────────


def test_load_pyproject_parses_slim_true(tmp_path: Path) -> None:
    content = textwrap.dedent(
        """
        [tool.uv-bundler]
        default_target = "t"

        [tool.uv-bundler.targets.t]
        format = "jar"
        entry_point = "app.main:run"
        platform = "linux"
        arch = "x86_64"
        slim = true
        """
    ).strip()
    path = write_pyproject(tmp_path, content)
    cfg = load_pyproject(path)
    tgt = cfg.resolve_target("t")
    assert tgt.slim is True


def test_load_pyproject_parses_slim_exclude(tmp_path: Path) -> None:
    content = textwrap.dedent(
        """
        [tool.uv-bundler]
        default_target = "t"

        [tool.uv-bundler.targets.t]
        format = "jar"
        entry_point = "app.main:run"
        platform = "linux"
        arch = "x86_64"
        slim = true
        slim_exclude = ["*.pyi", "tests/**"]
        """
    ).strip()
    path = write_pyproject(tmp_path, content)
    cfg = load_pyproject(path)
    tgt = cfg.resolve_target("t")
    assert tgt.slim_exclude == ["*.pyi", "tests/**"]


def test_load_pyproject_slim_defaults_false(tmp_path: Path) -> None:
    path = write_pyproject(tmp_path)
    cfg = load_pyproject(path)
    tgt = cfg.resolve_target("spark-prod")
    assert tgt.slim is False
    assert tgt.slim_exclude == []
