from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

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
    # sample dependency file and source file
    (site / "dep.txt").write_text("dep")
    (src / "app").mkdir()
    (src / "app" / "main.py").write_text("def run():\n    return 0\n")
    return StagingPaths(root=root, site_packages=site, sources=src)


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


def test_build_jar_detects_incompatible_binaries(tmp_path: Path) -> None:
    paths = make_staging(tmp_path)
    # introduce a macOS dylib in site-packages
    (paths.site_packages / "libfoo.dylib").write_text("bin")
    target = TargetConfig(platform="linux", arch="x86_64")
    out = tmp_path / "out.jar"
    with pytest.raises(ValueError):
        build_jar(paths, "app.main:run", target, out)
