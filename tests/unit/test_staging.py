from uv_bundler.adapters.fs import clean_staging, create_staging
from uv_bundler.services.staging import make_staging_paths


def test_create_and_clean_staging(tmp_path) -> None:
    paths = make_staging_paths(tmp_path)
    create_staging(paths)
    assert paths.root.exists()
    assert paths.site_packages.exists()
    assert paths.sources.exists()
    clean_staging(paths)
    assert not paths.root.exists()
