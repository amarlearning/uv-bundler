from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

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
