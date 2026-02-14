import pytest

from uv_pack.domain.platforms import pep508_platform


def test_pep508_platform_linux_x86_64() -> None:
    assert pep508_platform("linux", "x86_64") == "x86_64-unknown-linux-gnu"


def test_pep508_platform_linux_arm64() -> None:
    assert pep508_platform("linux", "aarch64") == "aarch64-unknown-linux-gnu"


def test_pep508_platform_macos_variants() -> None:
    assert pep508_platform("macos", "x86_64") == "x86_64-apple-darwin"
    assert pep508_platform("macos", "aarch64") == "aarch64-apple-darwin"


def test_pep508_platform_windows() -> None:
    assert pep508_platform("windows", "x86_64") == "x86_64-pc-windows-msvc"
    assert pep508_platform("windows", "aarch64") == "aarch64-pc-windows-msvc"


def test_pep508_platform_missing_values() -> None:
    with pytest.raises(ValueError):
        pep508_platform(None, "x86_64")  # type: ignore[arg-type]


def test_pep508_platform_invalid_combo() -> None:
    with pytest.raises(ValueError):
        pep508_platform("plan9", "mips")
