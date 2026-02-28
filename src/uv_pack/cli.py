from __future__ import annotations

import os
from pathlib import Path

import typer

from uv_pack.adapters.fs import clean_staging, create_staging
from uv_pack.adapters.process import run as process_run
from uv_pack.domain.config import (
    TargetConfig,
    UvPackConfig,
    assert_module_path_exists,
)
from uv_pack.services.config_loader import load_pyproject, merge_overrides
from uv_pack.services.packager import build_jar, build_pex, build_zip
from uv_pack.services.resolver import compile_lockfile, install_dependencies
from uv_pack.services.staging import StagingPaths, make_staging_paths

app = typer.Typer(help="uv-pack: Universal cross-platform Python packager powered by uv")


def _stage_sources(project_root: Path, dest: Path) -> None:
    skip = {".uv-pack", ".venv", ".venv_validation", "dist", "out", "__pycache__"}
    for child in project_root.iterdir():
        if child.name in skip:
            continue
        target = dest / child.name
        if child.is_dir():
            for sub in child.rglob("*"):
                rel = sub.relative_to(child)
                out_path = target / rel
                if sub.is_dir():
                    out_path.mkdir(parents=True, exist_ok=True)
                else:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(sub.read_bytes())
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(child.read_bytes())


def _output_root(pyproject: Path, cfg: UvPackConfig) -> Path:
    env_out = os.getenv("OUT_DIR")
    if env_out:
        return Path(env_out).resolve()
    base = cfg.global_config.output_base or "./dist"
    return (pyproject.parent / base).resolve()


def _artifact_path(out_root: Path, cfg: UvPackConfig, tgt: TargetConfig, suffix: str) -> Path:
    base_name = cfg.global_config.project_name or "app"
    platform = tgt.platform or "unknown-os"
    arch = tgt.arch or "unknown-arch"
    name = f"{base_name}-{str(platform).lower()}-{str(arch).lower()}{suffix}"
    return out_root / name


def _resolve_and_install(
    pyproject: Path, tgt: TargetConfig, paths: StagingPaths, staging_base: Path
) -> None:
    # Resolve and install dependencies
    staging_base.mkdir(exist_ok=True)
    lock_file = staging_base / "resolved.lock"
    typer.echo(f"Resolving dependencies for {tgt.platform}/{tgt.arch}...")
    if compile_lockfile(pyproject, tgt, lock_file, process_run, cwd=pyproject.parent) != 0:
        typer.echo("Failed to resolve dependencies")
        raise typer.Exit(code=1)

    typer.echo("Installing dependencies into staging...")
    if (
        install_dependencies(lock_file, tgt, paths.site_packages, process_run, cwd=pyproject.parent)
        != 0
    ):
        typer.echo("Failed to install dependencies")
        raise typer.Exit(code=1)


@app.command("build")
def build(
    target: str | None = typer.Option(None, "--target", "-t", help="Build target name"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate and print actions without building"
    ),
    arch: str | None = typer.Option(None, help="Override target architecture"),
    platform: str | None = typer.Option(None, help="Override target platform"),
    python_version: str | None = typer.Option(None, help="Override Python version"),
    manylinux: str | None = typer.Option(None, help="Override manylinux version"),
) -> None:
    """
    Build artifacts for a target defined in pyproject.toml.
    Validates configuration and supports dry-run inspection of the build plan.
    """
    pyproject = Path("pyproject.toml").resolve()
    cfg = load_pyproject(pyproject)
    tgt = cfg.resolve_target(target)
    tgt = merge_overrides(
        tgt,
        {
            "arch": arch,
            "platform": platform,
            "python_version": python_version,
            "manylinux": manylinux,
        },
    )
    assert_module_path_exists(Path.cwd(), tgt.entry_point)

    if dry_run:
        typer.echo("uv-pack dry run")
        typer.echo(f"- target: {target or cfg.global_config.default_target}")
        typer.echo(f"- format: {tgt.format}")
        typer.echo(f"- entry_point: {tgt.entry_point}")
        typer.echo(f"- platform: {tgt.platform}, arch: {tgt.arch}")
        typer.echo(f"- python: {tgt.python_version}, manylinux: {tgt.manylinux}")
        return

    if not tgt.format or not tgt.entry_point:
        raise typer.Exit(code=1)
    staging_base = Path(".uv-pack")
    paths = make_staging_paths(staging_base)
    clean_staging(paths)
    create_staging(paths)

    try:
        _stage_sources(pyproject.parent, paths.sources)
        _resolve_and_install(pyproject, tgt, paths, staging_base)

        out_root = _output_root(pyproject, cfg)
        if tgt.format == "jar":
            output = _artifact_path(out_root, cfg, tgt, ".jar")
            build_jar(paths, tgt.entry_point, tgt, output)
            typer.echo(str(output))
        elif tgt.format == "zip":
            output = _artifact_path(out_root, cfg, tgt, ".zip")
            build_zip(paths, tgt.entry_point, output)
            typer.echo(str(output))
        elif tgt.format == "pex":
            output = _artifact_path(out_root, cfg, tgt, ".pex")
            code = build_pex(paths, tgt.entry_point, output, process_run)
            if code != 0:
                raise typer.Exit(code=code)
            typer.echo(str(output))
        else:
            raise typer.Exit(code=1)
    finally:
        clean_staging(paths)
