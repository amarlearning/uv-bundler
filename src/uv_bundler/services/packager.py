from __future__ import annotations

import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from uv_bundler.domain.config import TargetConfig
from uv_bundler.domain.platforms import wheel_platform_tag
from uv_bundler.services.bootstrap import render_bootstrap
from uv_bundler.services.resolver import Runner
from uv_bundler.services.staging import StagingPaths


@dataclass(frozen=True)
class PackageResult:
    output: Path


def _iter_files(base: Path) -> Iterable[tuple[Path, Path]]:
    for path in base.rglob("*"):
        if path.is_file():
            yield (path, path.relative_to(base))


def _compression_mode(target: TargetConfig) -> int:
    if (target.compression or "deflated").lower() == "stored":
        return ZIP_STORED
    return ZIP_DEFLATED


def _write_manifest(zf: ZipFile) -> None:
    content = "Manifest-Version: 1.0\nCreated-By: uv-bundler\n\n"
    zf.writestr("META-INF/MANIFEST.MF", content)


def _write_extra_files(zf: ZipFile, project_root: Path | None, extra_files: dict[str, str]) -> None:
    """Copy extra_files into the archive.  Keys are source paths relative to
    project root; values are archive destination paths."""
    if not project_root or not extra_files:
        return
    for src_rel, arc_dest in extra_files.items():
        src = project_root / src_rel
        if src.is_file():
            zf.write(src, arc_dest)


def _ensure_no_incompatible_binaries(paths: StagingPaths, target: TargetConfig) -> None:
    if (target.platform or "").lower() != "linux":
        return
    forbidden_exts = {".dylib", ".dll"}
    for base in (paths.site_packages, paths.sources):
        for fpath, _arc in _iter_files(base):
            if fpath.suffix.lower() in forbidden_exts:
                raise ValueError(f"Incompatible binary detected for Linux target: {fpath.name}")


def _warn_on_native_extensions(paths: StagingPaths) -> None:
    """zipimport cannot load ``.so`` files, so a JAR run in place fails on import."""
    native = [f.name for f, _ in _iter_files(paths.site_packages) if f.suffix == ".so"]
    if native:
        warnings.warn(
            f"{len(native)} native extension(s) (e.g. {native[0]}) bundled into a JAR; "
            "they cannot be imported from inside the archive. Use format = 'pex' instead.",
            stacklevel=2,
        )


def build_jar(
    paths: StagingPaths,
    entry_point: str,
    target: TargetConfig,
    output: Path,
    project_root: Path | None = None,
) -> PackageResult:
    _ensure_no_incompatible_binaries(paths, target)
    _warn_on_native_extensions(paths)
    compression = _compression_mode(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, mode="w", compression=compression) as zf:
        _write_manifest(zf)
        zf.writestr("__main__.py", render_bootstrap(entry_point))
        for fpath, arc in _iter_files(paths.site_packages):
            zf.write(fpath, f"site-packages/{arc.as_posix()}")
        for fpath, arc in _iter_files(paths.sources):
            zf.write(fpath, arc.as_posix())
        _write_extra_files(zf, project_root, target.extra_files)
    return PackageResult(output=output)


def build_zip(
    paths: StagingPaths,
    entry_point: str,
    target: TargetConfig,
    output: Path,
    project_root: Path | None = None,
) -> PackageResult:
    _ensure_no_incompatible_binaries(paths, target)
    compression = _compression_mode(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, mode="w", compression=compression) as zf:
        zf.writestr("__main__.py", render_bootstrap(entry_point))
        for fpath, arc in _iter_files(paths.site_packages):
            zf.write(fpath, f"site-packages/{arc.as_posix()}")
        for fpath, arc in _iter_files(paths.sources):
            zf.write(fpath, arc.as_posix())
        _write_extra_files(zf, project_root, target.extra_files)
    return PackageResult(output=output)


def _pex_platform_tag(target: TargetConfig) -> str:
    """Return a PEX ``--platform`` string, e.g. ``manylinux2014_x86_64-cp-310-cp310``."""
    pyver = (target.python_version or "3.10").replace(".", "")
    os_platform = wheel_platform_tag(
        target.platform or "linux", target.arch or "x86_64", target.manylinux
    )
    return f"{os_platform}-cp-{pyver}-cp{pyver}"


def build_pex_command(
    paths: StagingPaths,
    entry_point: str,
    output: Path,
    lock_file: Path | None = None,
    target: TargetConfig | None = None,
) -> list[str]:
    """Build the ``pex`` CLI command.  pex resolves *lock_file* itself (cached in ``$PEX_ROOT``)."""
    cmd = ["pex"]
    if lock_file is not None and lock_file.exists():
        cmd += ["-r", str(lock_file)]
    cmd += ["--sources-directory", str(paths.sources)]
    if target is not None:
        cmd += ["--platform", _pex_platform_tag(target)]
    cmd += ["--include-tools", "-e", entry_point, "-o", str(output)]
    return cmd


def build_pex(
    paths: StagingPaths,
    entry_point: str,
    output: Path,
    run: Runner,
    lock_file: Path | None = None,
    target: TargetConfig | None = None,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_pex_command(paths, entry_point, output, lock_file=lock_file, target=target)
    return int(run(cmd, cwd=paths.root))
