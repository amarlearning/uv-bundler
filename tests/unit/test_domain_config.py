import textwrap
from pathlib import Path

import pytest

from uv_pack.domain.config import GlobalConfig, UvPackConfig, assert_module_path_exists
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
    pyproject = textwrap.dedent("""
        [tool.uv-pack]
        default_target = "t"

        [tool.uv-pack.targets.t]
        format = "jar"
        entry_point = "app.main"
        """).strip()
    p = tmp_path / "pyproject.toml"
    p.write_text(pyproject)
    with pytest.raises(ValueError):
        _ = load_pyproject(p)
