import textwrap
from pathlib import Path

import pytest

from uv_pack.domain.config import (
    GlobalConfig,
    TargetConfig,
    UvPackConfig,
    assert_module_path_exists,
)
from uv_pack.services.config_loader import load_pyproject


def test_assert_module_path_exists_raises(tmp_path: Path) -> None:
    # No app module present
    with pytest.raises(FileNotFoundError):
        assert_module_path_exists(tmp_path, "app.main:run")


def test_resolve_target_requires_default(tmp_path: Path) -> None:
    cfg = UvPackConfig(global_config=GlobalConfig(), targets={})
    with pytest.raises(ValueError):
        cfg.resolve_target(None)


def test_invalid_entry_point_format_rejected(tmp_path: Path) -> None:
    pyproject = textwrap.dedent(
        """
        [tool.uv-pack]
        default_target = "t"

        [tool.uv-pack.targets.t]
        format = "jar"
        entry_point = "app.main"
        """
    ).strip()
    p = tmp_path / "pyproject.toml"
    p.write_text(pyproject)
    with pytest.raises(ValueError):
        _ = load_pyproject(p)


def test_resolve_target_merges_config_and_targets() -> None:
    global_cfg = GlobalConfig(default_target="spark-prod")
    target = TargetConfig(
        format="jar",
        entry_point="app.main:run",
        platform="linux",
        arch="x86_64",
        python_version="3.10",
        manylinux="2014",
        bundle="fat",
        include_binaries=True,
        compression="deflated",
    )
    cfg = UvPackConfig(global_config=global_cfg, targets={"spark-prod": target})
    resolved = cfg.resolve_target(None)
    assert resolved.entry_point == "app.main:run"
    assert resolved.platform == "linux"
    assert resolved.arch == "x86_64"
    assert resolved.python_version == "3.10"
    assert resolved.manylinux == "2014"


def test_resolve_target_missing_named_target_raises() -> None:
    global_cfg = GlobalConfig(default_target="spark-prod")
    cfg = UvPackConfig(global_config=global_cfg, targets={})
    with pytest.raises(KeyError):
        cfg.resolve_target("spark-prod")


def test_assert_module_path_exists_allows_missing_entry_point(tmp_path: Path) -> None:
    assert_module_path_exists(tmp_path, None)
