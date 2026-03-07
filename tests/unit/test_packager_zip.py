from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from uv_pack.domain.config import TargetConfig
from uv_pack.services.packager import build_zip
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


def test_build_zip_writes_structure(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "out.zip"
    res = build_zip(paths, "app.main:run", TargetConfig(), out)
    assert res.output == out
    with ZipFile(out) as zf:
        names = set(zf.namelist())
        assert "__main__.py" in names
        assert "site-packages/dep.txt" in names
        assert "app/main.py" in names
        # ZIP has no MANIFEST.MF (unlike JAR)
        assert "META-INF/MANIFEST.MF" not in names


def test_build_zip_bootstrap_contains_entry_point(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "out.zip"
    build_zip(paths, "mymod.sub:handler", TargetConfig(), out)
    with ZipFile(out) as zf:
        bootstrap = zf.read("__main__.py").decode()
    assert "mymod.sub" in bootstrap
    assert "handler" in bootstrap


# ── compression ───────────────────────────────────────────────────────────────


def test_build_zip_deflated_by_default(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    out = tmp_path / "out.zip"
    build_zip(paths, "app.main:run", TargetConfig(), out)
    with ZipFile(out) as zf:
        assert zf.getinfo("app/main.py").compress_type == ZIP_DEFLATED


def test_build_zip_stored_compression(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    target = TargetConfig(compression="stored")
    out = tmp_path / "out.zip"
    build_zip(paths, "app.main:run", target, out)
    with ZipFile(out) as zf:
        assert zf.getinfo("app/main.py").compress_type == ZIP_STORED


# ── extra_files ───────────────────────────────────────────────────────────────


def test_build_zip_extra_files_injected(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "config.yaml").write_text("env: prod\n")
    target = TargetConfig(extra_files={"config.yaml": "resources/config.yaml"})
    out = tmp_path / "out.zip"
    build_zip(paths, "app.main:run", target, out, project_root=project_root)
    with ZipFile(out) as zf:
        assert "resources/config.yaml" in zf.namelist()
        assert zf.read("resources/config.yaml") == b"env: prod\n"


def test_build_zip_extra_files_skips_missing_source(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    target = TargetConfig(extra_files={"no_such_file.yaml": "dest.yaml"})
    out = tmp_path / "out.zip"
    build_zip(paths, "app.main:run", target, out, project_root=project_root)
    with ZipFile(out) as zf:
        assert "dest.yaml" not in zf.namelist()
