from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from uv_pack.domain.config import TargetConfig
from uv_pack.services.packager import build_jar
from uv_pack.services.staging import StagingPaths


def make_staging(tmp_path: Path) -> StagingPaths:
    root = tmp_path / "staging"
    site = root / "site-packages"
    src = root / "src"
    for d in (site, src):
        d.mkdir(parents=True, exist_ok=True)
    (site / "dep.txt").write_text("dep")
    (src / "app").mkdir()
    (src / "app" / "main.py").write_text("def run():\n    return 0\n")
    return StagingPaths(root=root, site_packages=site, sources=src)


# ── archive structure ─────────────────────────────────────────────────────────


def test_build_jar_writes_structure(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    target = TargetConfig(platform="linux", arch="x86_64")
    out = tmp_path / "out.jar"
    res = build_jar(paths, "app.main:run", target, out)
    assert res.output == out
    with ZipFile(out) as zf:
        names = set(zf.namelist())
        assert "__main__.py" in names
        assert "META-INF/MANIFEST.MF" in names
        assert "site-packages/dep.txt" in names
        assert "app/main.py" in names


def test_build_jar_manifest_content(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "out.jar"
    build_jar(paths, "app.main:run", TargetConfig(platform="linux", arch="x86_64"), out)
    with ZipFile(out) as zf:
        manifest = zf.read("META-INF/MANIFEST.MF").decode()
    assert "Manifest-Version: 1.0" in manifest
    assert "uv-pack" in manifest


def test_build_jar_bootstrap_contains_entry_point(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "out.jar"
    build_jar(paths, "mymod.sub:handler", TargetConfig(platform="linux", arch="x86_64"), out)
    with ZipFile(out) as zf:
        bootstrap = zf.read("__main__.py").decode()
    assert "mymod.sub" in bootstrap
    assert "handler" in bootstrap


# ── binary safety (Linux targets only) ───────────────────────────────────────


def test_build_jar_detects_incompatible_binaries(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    (paths.site_packages / "libfoo.dylib").write_text("bin")
    target = TargetConfig(platform="linux", arch="x86_64")
    with pytest.raises(ValueError, match="Incompatible binary"):
        build_jar(paths, "app.main:run", target, tmp_path / "out.jar")


def test_build_jar_detects_dll_for_linux(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    (paths.site_packages / "foo.dll").write_text("bin")
    target = TargetConfig(platform="linux", arch="x86_64")
    with pytest.raises(ValueError, match="Incompatible binary"):
        build_jar(paths, "app.main:run", target, tmp_path / "out.jar")


def test_build_jar_ignores_binaries_for_non_linux_targets(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    (paths.site_packages / "libfoo.dylib").write_text("bin")
    target = TargetConfig(platform="macos", arch="x86_64")
    res = build_jar(paths, "app.main:run", target, tmp_path / "out.jar")
    assert res.output.exists()


# ── compression ───────────────────────────────────────────────────────────────


def test_build_jar_deflated_compression_by_default(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "out.jar"
    build_jar(paths, "app.main:run", TargetConfig(platform="linux", arch="x86_64"), out)
    with ZipFile(out) as zf:
        assert zf.getinfo("app/main.py").compress_type == ZIP_DEFLATED


def test_build_jar_stored_compression(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    target = TargetConfig(platform="linux", arch="x86_64", compression="stored")
    out = tmp_path / "out.jar"
    build_jar(paths, "app.main:run", target, out)
    with ZipFile(out) as zf:
        assert zf.getinfo("app/main.py").compress_type == ZIP_STORED


# ── extra_files ───────────────────────────────────────────────────────────────


def test_build_jar_extra_files_injected(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    project_root = tmp_path / "project"
    (project_root / "config").mkdir(parents=True)
    (project_root / "config" / "prod.yaml").write_text("key: value\n")
    target = TargetConfig(
        platform="linux",
        arch="x86_64",
        extra_files={"config/prod.yaml": "resources/config.yaml"},
    )
    out = tmp_path / "out.jar"
    build_jar(paths, "app.main:run", target, out, project_root=project_root)
    with ZipFile(out) as zf:
        assert "resources/config.yaml" in zf.namelist()
        assert zf.read("resources/config.yaml") == b"key: value\n"


def test_build_jar_extra_files_skips_missing_source(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    target = TargetConfig(
        platform="linux",
        arch="x86_64",
        extra_files={"does_not_exist.yaml": "dest.yaml"},
    )
    out = tmp_path / "out.jar"
    build_jar(paths, "app.main:run", target, out, project_root=project_root)
    with ZipFile(out) as zf:
        assert "dest.yaml" not in zf.namelist()


def test_build_jar_no_project_root_skips_extra_files(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    target = TargetConfig(
        platform="linux",
        arch="x86_64",
        extra_files={"config/prod.yaml": "resources/config.yaml"},
    )
    out = tmp_path / "out.jar"
    build_jar(paths, "app.main:run", target, out, project_root=None)
    with ZipFile(out) as zf:
        assert "resources/config.yaml" not in zf.namelist()
