from __future__ import annotations

import shutil

from uv_bundler.services.staging import StagingPaths


def create_staging(paths: StagingPaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.site_packages.mkdir(parents=True, exist_ok=True)
    paths.sources.mkdir(parents=True, exist_ok=True)


def clean_staging(paths: StagingPaths) -> None:
    if paths.root.exists():
        shutil.rmtree(paths.root)
