from __future__ import annotations

from typing import Final

_MAP: Final[dict[tuple[str, str], str]] = {
    ("linux", "x86_64"): "x86_64-unknown-linux-gnu",
    ("linux", "aarch64"): "aarch64-unknown-linux-gnu",
    ("macos", "x86_64"): "x86_64-apple-darwin",
    ("macos", "aarch64"): "aarch64-apple-darwin",
    ("windows", "x86_64"): "x86_64-pc-windows-msvc",
    ("windows", "aarch64"): "aarch64-pc-windows-msvc",
}


def pep508_platform(platform: str | None, arch: str | None, manylinux: str | None = None) -> str:
    """Return the uv --python-platform string for the given target.

    For Linux targets with a manylinux constraint, returns the manylinux-tagged
    platform string (e.g. ``x86_64-manylinux2014``) so that uv selects the
    correct manylinux wheels instead of generic linux ones.
    """
    if not platform or not arch:
        raise ValueError("platform and arch are required")
    plat = platform.lower()
    ar = arch.lower()
    key = (plat, ar)
    if key not in _MAP:
        raise ValueError(f"unsupported platform combo: {platform}/{arch}")
    if plat == "linux" and manylinux:
        # "2010" / "2014" → legacy short tags; numeric string → glibc minor version
        if manylinux in ("2010", "2014"):
            return f"{ar}-manylinux{manylinux}"
        return f"{ar}-manylinux_2_{manylinux}"
    return _MAP[key]
