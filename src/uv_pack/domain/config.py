from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class GlobalConfig(BaseModel):
    project_name: str | None = None
    default_target: str | None = None
    output_base: str | None = None

    model_config = {"frozen": True}


class TargetConfig(BaseModel):
    format: str | None = None
    entry_point: str | None = None
    platform: str | None = None
    arch: str | None = None
    python_version: str | None = None
    manylinux: str | None = None
    bundle: str | None = None
    include_binaries: bool | None = None
    compression: str | None = None
    exclude: list[str] = Field(default_factory=list)
    extra_files: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_entry_point_format(self) -> TargetConfig:
        if self.entry_point:
            parts = self.entry_point.split(":", 1)
            if ":" not in self.entry_point or not parts[0] or not parts[1]:
                raise ValueError("entry_point must be in the form 'module.submodule:function'")
        return self


class UvPackConfig(BaseModel):
    global_config: GlobalConfig = Field(default_factory=GlobalConfig)
    targets: dict[str, TargetConfig] = Field(default_factory=dict)

    model_config = {"frozen": True}

    def resolve_target(self, name: str | None) -> TargetConfig:
        target_name = name or self.global_config.default_target
        if not target_name:
            raise ValueError("No target specified and 'default_target' not set in config")
        if target_name not in self.targets:
            raise KeyError(f"Target '{target_name}' not found in configuration")
        tgt = self.targets[target_name]
        # Merge global fallbacks with target specifics (target wins)
        return TargetConfig(
            format=tgt.format,
            entry_point=tgt.entry_point,
            platform=tgt.platform,
            arch=tgt.arch,
            python_version=tgt.python_version,
            manylinux=tgt.manylinux,
            bundle=tgt.bundle,
            include_binaries=tgt.include_binaries,
            compression=tgt.compression,
            exclude=tgt.exclude or [],
            extra_files=tgt.extra_files or {},
        )


def assert_module_path_exists(project_root: Path, entry_point: str | None) -> None:
    if not entry_point:
        return
    module_str, _func = entry_point.split(":")
    parts = module_str.split(".")
    # Accept either package directory or .py file
    pkg_path = project_root.joinpath(*parts)
    file_path = project_root.joinpath(*parts[:-1], f"{parts[-1]}.py")
    if not pkg_path.exists() and not file_path.exists():
        raise FileNotFoundError(f"Entry point module '{module_str}' not found under {project_root}")
