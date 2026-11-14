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
        return f"{ar}-{_manylinux_tag(manylinux)}"
    return _MAP[key]


def _manylinux_tag(manylinux: str) -> str:
    """``"2010"``/``"2014"`` → legacy alias; numeric string → glibc minor (``manylinux_2_31``)."""
    if manylinux in ("2010", "2014"):
        return f"manylinux{manylinux}"
    return f"manylinux_2_{manylinux}"


def wheel_platform_tag(platform: str, arch: str, manylinux: str | None = None) -> str:
    """Return the PEP 425 wheel platform tag, e.g. ``manylinux2014_x86_64``."""
    plat, ar = platform.lower(), arch.lower()
    if plat == "linux":
        return f"{_manylinux_tag(manylinux or '2014')}_{ar}"
    if plat == "macos":
        # Apple Silicon wheels are tagged arm64 and require macOS 11+.
        return "macosx_11_0_arm64" if ar == "aarch64" else f"macosx_10_9_{ar}"
    if plat == "windows":
        return "win_arm64" if ar == "aarch64" else "win_amd64"
    raise ValueError(f"unsupported platform: {platform}")
