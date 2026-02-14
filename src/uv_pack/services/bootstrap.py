from __future__ import annotations


def render_bootstrap(entry_point: str) -> str:
    module, func = entry_point.split(":", 1)
    return "\n".join(
        [
            "import importlib",
            "import sys",
            "",
            "def _run() -> int:",
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
