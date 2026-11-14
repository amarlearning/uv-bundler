from __future__ import annotations


def render_bootstrap(entry_point: str) -> str:
    """Render ``__main__.py`` so ``python artifact.zip`` calls *entry_point*.

    Dependencies live at the archive root, which Python already puts on sys.path
    when it runs a zip, so no path setup is needed.
    """
    module, func = entry_point.split(":", 1)
    return "\n".join(
        [
            "import importlib",
            "",
            "def _run() -> int:",
            f"    mod = importlib.import_module({module!r})",
            f"    fn = getattr(mod, {func!r})",
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
