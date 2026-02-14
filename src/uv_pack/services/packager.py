from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable
from zipfile import ZIP_DEFLATED, ZipFile

from uv_pack.domain.config import TargetConfig
from uv_pack.services.bootstrap import render_bootstrap
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
