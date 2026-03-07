from __future__ import annotations


def render_bootstrap(entry_point: str) -> str:
    module, func = entry_point.split(":", 1)
    return "\n".join(
        [
            "import importlib",
            "import sys",
            "from pathlib import Path",
            "",
            "def _setup_path() -> None:",
            "    # When running as a zipapp (python myapp.jar), sys.path[0] is the",
            "    # zip/jar file itself.  Python's zipimport supports sub-paths like",
            "    # 'myapp.jar/site-packages' as sys.path entries, so we add that",
            "    # directly without a filesystem .exists() check (which would fail",
            "    # because the sub-path is inside the archive, not on disk).",
            "    archive = Path(sys.path[0]) if sys.path else None",
            "    if archive is not None and archive.is_file():",
            "        sys.path.insert(0, str(archive) + '/site-packages')",
            "    else:",
            "        # Extracted / development layout: look next to __file__",
            "        root = Path(__file__).parent",
            "        site_packages = root / 'site-packages'",
            "        if site_packages.exists():",
            "            sys.path.insert(0, str(site_packages))",
            "",
            "def _run() -> int:",
            "    _setup_path()",
            f"    mod = importlib.import_module('{module}')",
            f"    fn = getattr(mod, '{func}')",
            "    res = fn()",
            "    if isinstance(res, int):",
            "        return res",
            "    return 0",
            "",
            "if __name__ == '__main__':",
            "    raise SystemExit(_run())",
            "",
        ]
    )
