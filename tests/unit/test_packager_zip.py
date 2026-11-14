from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from uv_bundler.domain.config import TargetConfig
from uv_bundler.services.packager import build_zip
from uv_bundler.services.staging import StagingPaths


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
        assert "dep.txt" in names  # deps at archive root
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


# ── binary safety (Linux targets only) ───────────────────────────────────────


def test_build_zip_detects_incompatible_binaries(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    (paths.site_packages / "libfoo.dylib").write_text("bin")
    target = TargetConfig(platform="linux", arch="aarch64")
    with pytest.raises(ValueError, match="Incompatible binary"):
        build_zip(paths, "app.main:run", target, tmp_path / "out.zip")


def test_build_zip_allows_so_files(tmp_path: Path) -> None:
    """Lambda extracts the ZIP, so native .so extensions are fine."""
    paths = make_staging(tmp_path)
    (paths.site_packages / "_core.so").write_text("bin")
    target = TargetConfig(platform="linux", arch="x86_64")
    assert build_zip(paths, "app.main:run", target, tmp_path / "out.zip").output.exists()


def test_build_zip_runs_with_deps_at_root(tmp_path: Path) -> None:
    """`python app.zip` and Lambda-style imports both see deps at the archive root."""
    paths = make_staging(tmp_path)
    (paths.sources / "app" / "__init__.py").write_text("")
    (paths.site_packages / "greet").mkdir()
    (paths.site_packages / "greet" / "__init__.py").write_text("WORD = 'hi'\n")
    (paths.site_packages / "bin").mkdir()
    (paths.site_packages / "bin" / "greet-cli").write_text("#!/host/python\n")
    (paths.sources / "app" / "main.py").write_text(
        "import greet\n\ndef run():\n    print(greet.WORD)\n    return 0\n"
    )
    out = tmp_path / "out.zip"
    build_zip(paths, "app.main:run", TargetConfig(), out)
    run = subprocess.run(  # noqa: S603 - runs the artifact this test just built
        [sys.executable, str(out)], capture_output=True, text=True, check=True
    )
    assert run.stdout.strip() == "hi"
    # Lambda / --py-files style: only the archive root on sys.path, no __main__.
    handler_import = "import sys; sys.path.insert(0, sys.argv[1]); import app.main; app.main.run()"
    run = subprocess.run(  # noqa: S603
        [sys.executable, "-c", handler_import, str(out)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert run.stdout.strip() == "hi"
    with ZipFile(out) as zf:
        assert "bin/greet-cli" not in zf.namelist()


def test_build_zip_rejects_source_dependency_collision(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    (paths.site_packages / "app").mkdir()
    (paths.site_packages / "app" / "main.py").write_text("")
    with pytest.raises(ValueError, match="collides"):
        build_zip(paths, "app.main:run", TargetConfig(), tmp_path / "out.zip")
