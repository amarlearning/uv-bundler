import textwrap
from pathlib import Path

import pytest

from uv_bundler.domain.config import (
    GlobalConfig,
    TargetConfig,
    UvPackConfig,
    assert_module_path_exists,
)
from uv_bundler.services.config_loader import load_pyproject

# ── assert_module_path_exists ─────────────────────────────────────────────────


def test_assert_module_path_exists_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        assert_module_path_exists(tmp_path, "app.main:run")


def test_assert_module_path_exists_allows_none_entry_point(tmp_path: Path) -> None:
    # No entry point — should be a no-op
    assert_module_path_exists(tmp_path, None)


def test_assert_module_path_exists_accepts_package_dir(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    # Should not raise — app package exists
    assert_module_path_exists(tmp_path, "app:run")


def test_assert_module_path_exists_accepts_py_file(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("def run(): pass\n")
    # Should not raise — app/main.py exists
    assert_module_path_exists(tmp_path, "app.main:run")


def test_assert_module_path_exists_raises_for_missing_submodule(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    # app/ exists but app/missing.py does not
    with pytest.raises(FileNotFoundError):
        assert_module_path_exists(tmp_path, "app.missing:run")


# ── UvPackConfig.resolve_target ───────────────────────────────────────────────


def test_resolve_target_requires_default() -> None:
    cfg = UvPackConfig(global_config=GlobalConfig(), targets={})
    with pytest.raises(ValueError):
        cfg.resolve_target(None)


def test_resolve_target_missing_named_target_raises() -> None:
    global_cfg = GlobalConfig(default_target="spark-prod")
    cfg = UvPackConfig(global_config=global_cfg, targets={})
    with pytest.raises(KeyError):
        cfg.resolve_target("spark-prod")


def test_resolve_target_merges_config_and_targets() -> None:
    global_cfg = GlobalConfig(default_target="spark-prod")
    target = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="x86_64",
        python_version="3.10",
        manylinux="2014",
        compression="deflated",
    )
    cfg = UvPackConfig(global_config=global_cfg, targets={"spark-prod": target})
    resolved = cfg.resolve_target(None)
    assert resolved.entry_point == "app.main:run"
    assert resolved.platform == "linux"
    assert resolved.arch == "x86_64"
    assert resolved.python_version == "3.10"
    assert resolved.manylinux == "2014"


def test_resolve_target_by_explicit_name() -> None:
    global_cfg = GlobalConfig(default_target="default-tgt")
    cfg = UvPackConfig(
        global_config=global_cfg,
        targets={
            "default-tgt": TargetConfig(format="jar", entry_point="a:b"),
            "other-tgt": TargetConfig(format="zip", entry_point="c:d"),
        },
    )
    resolved = cfg.resolve_target("other-tgt")
    assert resolved.format == "zip"
    assert resolved.entry_point == "c:d"


# ── TargetConfig validation ───────────────────────────────────────────────────


def test_invalid_entry_point_format_rejected(tmp_path: Path) -> None:
    pyproject = textwrap.dedent(
        """
        [tool.uv-bundler]
        default_target = "t"

        [tool.uv-bundler.targets.t]
        format = "jar"
        entry_point = "app.main"
        """
    ).strip()
    p = tmp_path / "pyproject.toml"
    p.write_text(pyproject)
    with pytest.raises(ValueError):
        _ = load_pyproject(p)


def test_entry_point_empty_module_rejected() -> None:
    with pytest.raises(ValueError):
        TargetConfig(entry_point=":run")


def test_entry_point_empty_function_rejected() -> None:
    with pytest.raises(ValueError):
        TargetConfig(entry_point="app.main:")


def test_target_config_extra_files_default_empty() -> None:
    tgt = TargetConfig()
    assert tgt.extra_files == {}


def test_target_config_exclude_default_empty() -> None:
    tgt = TargetConfig()
    assert tgt.exclude == []


# ── slim / slim_exclude ───────────────────────────────────────────────────────


def test_slim_defaults_to_false() -> None:
    tgt = TargetConfig()
    assert tgt.slim is False


def test_slim_exclude_defaults_to_empty() -> None:
    tgt = TargetConfig()
    assert tgt.slim_exclude == []


def test_slim_and_slim_exclude_set() -> None:
    tgt = TargetConfig(slim=True, slim_exclude=["*.pyi", "tests/**"])
    assert tgt.slim is True
    assert tgt.slim_exclude == ["*.pyi", "tests/**"]


def test_resolve_target_passes_through_slim_fields() -> None:
    global_cfg = GlobalConfig(default_target="t")
    target = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        slim=True,
        slim_exclude=["*.pyi"],
    )
    cfg = UvPackConfig(global_config=global_cfg, targets={"t": target})
    resolved = cfg.resolve_target(None)
    assert resolved.slim is True
    assert resolved.slim_exclude == ["*.pyi"]


def test_resolve_target_slim_defaults_false_when_not_set() -> None:
    global_cfg = GlobalConfig(default_target="t")
    cfg = UvPackConfig(
        global_config=global_cfg,
        targets={"t": TargetConfig(format="jar", entry_point="app.main:run")},
    )
    resolved = cfg.resolve_target(None)
    assert resolved.slim is False
    assert resolved.slim_exclude == []
