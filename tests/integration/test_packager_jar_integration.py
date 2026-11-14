from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from uv_bundler.adapters.fs import clean_staging, create_staging
from uv_bundler.domain.config import TargetConfig
from uv_bundler.services.packager import build_jar
from uv_bundler.services.staging import make_staging_paths


def test_jar_packager_integration(tmp_path: Path) -> None:
    paths = make_staging_paths(tmp_path)
    try:
        create_staging(paths)
        # simulate staged content
        (paths.site_packages / "pkg").mkdir(parents=True, exist_ok=True)
        (paths.site_packages / "pkg" / "__init__.py").write_text("# pkg")
        (paths.sources / "app").mkdir(parents=True, exist_ok=True)
        (paths.sources / "app" / "main.py").write_text("def run():\n    return 0\n")
        out = tmp_path / "artifact.jar"
        target = TargetConfig(platform="linux", arch="x86_64")
        build_jar(paths, "app.main:run", target, out)
        with ZipFile(out) as zf:
            names = set(zf.namelist())
            assert "META-INF/MANIFEST.MF" in names
            assert "__main__.py" in names
            assert "pkg/__init__.py" in names  # deps at archive root
            assert "app/main.py" in names
    finally:
        clean_staging(paths)


def test_jar_slim_mode_no_site_packages(tmp_path: Path) -> None:
    """In slim mode site-packages dir is empty; JAR must contain only sources + bootstrap."""
    paths = make_staging_paths(tmp_path)
    try:
        create_staging(paths)
        # site-packages intentionally left empty (slim: deps never installed)
        (paths.sources / "app").mkdir(parents=True, exist_ok=True)
        (paths.sources / "app" / "main.py").write_text("def run():\n    return 0\n")
        out = tmp_path / "artifact-slim.jar"
        target = TargetConfig(platform="linux", arch="x86_64")
        build_jar(paths, "app.main:run", target, out)
        with ZipFile(out) as zf:
            names = set(zf.namelist())
        assert "META-INF/MANIFEST.MF" in names
        assert "__main__.py" in names
        assert "app/main.py" in names
        assert not any(n.startswith("pkg/") for n in names)
    finally:
        clean_staging(paths)
