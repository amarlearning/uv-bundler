from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from uv_pack.domain.config import TargetConfig
from uv_pack.services.bootstrap import render_bootstrap
from uv_pack.services.resolver import Runner
from uv_pack.services.staging import StagingPaths


@dataclass(frozen=True)
class PackageResult:
    output: Path


def _iter_files(base: Path) -> Iterable[tuple[Path, Path]]:
    for path in base.rglob("*"):
        if path.is_file():
            yield (path, path.relative_to(base))


def _write_manifest(zf: ZipFile) -> None:
    content = "Manifest-Version: 1.0\nCreated-By: uv-pack\n\n"
    zf.writestr("META-INF/MANIFEST.MF", content)


def _ensure_no_incompatible_binaries(paths: StagingPaths, target: TargetConfig) -> None:
    if (target.platform or "").lower() != "linux":
        return
    forbidden_exts = {".dylib", ".dll"}
    for base in (paths.site_packages, paths.sources):
        for fpath, _arc in _iter_files(base):
            if fpath.suffix.lower() in forbidden_exts:
                raise ValueError(f"Incompatible binary detected for Linux target: {fpath.name}")


def build_jar(
    paths: StagingPaths, entry_point: str, target: TargetConfig, output: Path
) -> PackageResult:
    _ensure_no_incompatible_binaries(paths, target)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zf:
        _write_manifest(zf)
        zf.writestr("__main__.py", render_bootstrap(entry_point))
        for fpath, arc in _iter_files(paths.site_packages):
            zf.write(fpath, f"site-packages/{arc.as_posix()}")
        for fpath, arc in _iter_files(paths.sources):
            zf.write(fpath, arc.as_posix())
    return PackageResult(output=output)


def build_zip(paths: StagingPaths, entry_point: str, output: Path) -> PackageResult:
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("__main__.py", render_bootstrap(entry_point))
        # Add site-packages to root of zip to make it importable
        # However, to avoid conflicts, we keep it in site-packages/
        # and rely on bootstrap.py to add it to sys.path
        for fpath, arc in _iter_files(paths.site_packages):
            zf.write(fpath, f"site-packages/{arc.as_posix()}")
        for fpath, arc in _iter_files(paths.sources):
            zf.write(fpath, arc.as_posix())
    return PackageResult(output=output)


def build_pex_command(paths: StagingPaths, entry_point: str, output: Path) -> list[str]:
    # PEX command needs both sources and site-packages (dependencies)
    cmd = [
        "pex",
        "-D",
        str(paths.sources),
        "-D",
        str(paths.site_packages),
        "--sources-directory",
        str(paths.sources),
        "--include-tools",
        "-e",
        entry_point,
        "-o",
        str(output),
    ]
    return cmd


def build_pex(paths: StagingPaths, entry_point: str, output: Path, run: Runner) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_pex_command(paths, entry_point, output)
    return int(run(cmd, cwd=paths.root))
