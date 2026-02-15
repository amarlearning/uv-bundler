from pathlib import Path

from uv_pack.adapters.fs import clean_staging, create_staging
from uv_pack.services.staging import StagingPaths


def make_paths(tmp_path: Path) -> StagingPaths:
    root = tmp_path / "staging"
    site_packages = root / "site-packages"
    sources = root / "src"
    return StagingPaths(root=root, site_packages=site_packages, sources=sources)


def test_create_staging_creates_directories(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    create_staging(paths)
    assert paths.root.is_dir()
    assert paths.site_packages.is_dir()
    assert paths.sources.is_dir()


def test_clean_staging_removes_existing_root(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    create_staging(paths)
    assert paths.root.exists()
    clean_staging(paths)
    assert not paths.root.exists()


def test_clean_staging_is_noop_when_root_missing(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    assert not paths.root.exists()
    clean_staging(paths)
    assert not paths.root.exists()
