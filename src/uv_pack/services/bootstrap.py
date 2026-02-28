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
            "    # Add site-packages to sys.path",
            "    root = Path(__file__).parent",
            "    site_packages = root / 'site-packages'",
            "    if site_packages.exists():",
            "        sys.path.insert(0, str(site_packages))",
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
