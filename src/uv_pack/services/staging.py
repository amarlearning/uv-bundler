from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StagingPaths:
    root: Path
    site_packages: Path
    sources: Path


def make_staging_paths(base_dir: Path) -> StagingPaths:
    root = base_dir / "staging"
    return StagingPaths(root=root, site_packages=root / "site-packages", sources=root / "src")
