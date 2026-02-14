from __future__ import annotations

from pathlib import Path

from uv_pack.adapters.fs import clean_staging, create_staging
from uv_pack.services.packager import build_pex
from uv_pack.services.staging import make_staging_paths

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
