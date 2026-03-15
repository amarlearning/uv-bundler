from __future__ import annotations

from pathlib import Path

from uv_bundler.adapters.fs import clean_staging, create_staging
from uv_bundler.services.packager import build_pex
from uv_bundler.services.staging import make_staging_paths

"""
This test uses a stubbed runner and does not require pex to be installed.
It ensures we invoke the process with the proper working directory and arguments.
"""


def test_build_pex_integration_with_stub_runner(tmp_path: Path) -> None:
    paths = make_staging_paths(tmp_path)
    try:
        create_staging(paths)
        (paths.sources / "app").mkdir(parents=True, exist_ok=True)
        (paths.sources / "app" / "main.py").write_text("def run():\n    return 0\n")
        out = tmp_path / "app.pex"

        observed = {"cwd": None, "args": None}

        def stub(args: list[str], cwd: Path | None = None) -> int:
            observed["cwd"] = cwd
            observed["args"] = args
            return 0

        rc = build_pex(paths, "app.main:run", out, run=stub)
        assert rc == 0
        assert observed["cwd"] == paths.root
        assert isinstance(observed["args"], list) and observed["args"][0] == "pex"
    finally:
        clean_staging(paths)


def test_build_pex_slim_mode_no_requirements(tmp_path: Path) -> None:
    """In slim mode lock_file is None; pex command must not include -r."""
    paths = make_staging_paths(tmp_path)
    try:
        create_staging(paths)
        (paths.sources / "app").mkdir(parents=True, exist_ok=True)
        (paths.sources / "app" / "main.py").write_text("def run():\n    return 0\n")
        out = tmp_path / "app-slim.pex"

        observed: dict[str, object] = {}

        def stub(args: list[str], cwd: Path | None = None) -> int:
            observed["args"] = args
            return 0

        # slim mode: lock_file=None (never created since resolve step was skipped)
        rc = build_pex(paths, "app.main:run", out, run=stub, lock_file=None)
        assert rc == 0
        assert "-r" not in observed["args"]  # type: ignore[operator]
        assert "--sources-directory" in observed["args"]  # type: ignore[operator]
    finally:
        clean_staging(paths)
