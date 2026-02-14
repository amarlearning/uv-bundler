from __future__ import annotations

from pathlib import Path

import typer

from uv_pack.domain.config import assert_module_path_exists
from uv_pack.services.config_loader import load_pyproject, merge_overrides

app = typer.Typer(help="uv-pack: Universal cross-platform Python packager powered by uv")


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
    In Phase 1, this command validates configuration and supports dry-run only.
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
        typer.echo("uv-pack dry run (Phase 1 skeleton)")
        typer.echo(f"- target: {target or cfg.global_config.default_target}")
        typer.echo(f"- format: {tgt.format}")
        typer.echo(f"- entry_point: {tgt.entry_point}")
        typer.echo(f"- platform: {tgt.platform}, arch: {tgt.arch}")
        typer.echo(f"- python: {tgt.python_version}, manylinux: {tgt.manylinux}")
        typer.echo("- no build executed (use future Phase 2+ for actual packaging)")
        return

    raise typer.Exit(code=1)
