import time
from pathlib import Path

from uv_pack.domain.config import TargetConfig
from uv_pack.services.packager import build_jar
from uv_pack.services.staging import StagingPaths


def make_large_staging(tmp_path: Path, count: int) -> StagingPaths:
    root = tmp_path / "staging"
    site = root / "site-packages"
    src = root / "src"
    site.mkdir(parents=True, exist_ok=True)
    src.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (site / f"dep{i}.txt").write_text(str(i))
    (src / "app").mkdir()
    (src / "app" / "main.py").write_text("def run():\n    return 0\n")
    return StagingPaths(root=root, site_packages=site, sources=src)


def test_build_jar_benchmark(tmp_path: Path) -> None:
    paths = make_large_staging(tmp_path, 200)
    target = TargetConfig(platform="linux", arch="x86_64")
    out = tmp_path / "bench.jar"
    start = time.perf_counter()
    res = build_jar(paths, "app.main:run", target, out)
    duration = time.perf_counter() - start
    assert res.output == out
    assert duration >= 0.0
