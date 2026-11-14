from __future__ import annotations

import importlib
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from uv_bundler.domain.config import GlobalConfig, TargetConfig, UvBundlerConfig


def _coerce_target(data: Mapping[str, Any]) -> TargetConfig:
    return TargetConfig(
        format=data.get("format"),
        entry_point=data.get("entry_point"),
        platform=data.get("platform"),
        arch=data.get("arch"),
        python_version=data.get("python_version"),
        manylinux=data.get("manylinux"),
        bundle=data.get("bundle"),
        include_binaries=data.get("include_binaries"),
        compression=data.get("compression"),
        exclude=list(data.get("exclude", [])),
        extra_files=dict(data.get("extra_files", {})),
        slim=bool(data.get("slim", False)),
        slim_exclude=list(data.get("slim_exclude", [])),
    )


def load_pyproject(path: Path) -> UvBundlerConfig:
    if not path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {path}")
    loader_name = "tomllib" if sys.version_info >= (3, 11) else "tomli"
    _toml = importlib.import_module(loader_name)
    with path.open("rb") as f:
        raw = _toml.load(f)
    tool = raw.get("tool", {})
    uvp = tool.get("uv-bundler", {})
    global_cfg = GlobalConfig(
        project_name=uvp.get("project_name"),
        default_target=uvp.get("default_target"),
        output_base=uvp.get("output_base"),
    )
    targets_raw = uvp.get("targets", {})
    targets: dict[str, TargetConfig] = {}
    for name, cfg in targets_raw.items():
        targets[name] = _coerce_target(cfg or {})
    try:
        return UvBundlerConfig(global_config=global_cfg, targets=targets)
    except ValidationError as e:
        raise ValueError(f"Invalid uv-bundler configuration: {e}") from e


def merge_overrides(target: TargetConfig, overrides: Mapping[str, Any]) -> TargetConfig:
    data = target.model_dump()
    for key, value in overrides.items():
        if key in data and value is not None:
            data[key] = value
    return TargetConfig(**data)
