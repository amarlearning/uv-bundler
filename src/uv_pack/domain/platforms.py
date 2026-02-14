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


def pep508_platform(platform: str | None, arch: str | None) -> str:
    if not platform or not arch:
        raise ValueError("platform and arch are required")
    key = (platform.lower(), arch.lower())
    if key not in _MAP:
        raise ValueError(f"unsupported platform combo: {platform}/{arch}")
    return _MAP[key]
