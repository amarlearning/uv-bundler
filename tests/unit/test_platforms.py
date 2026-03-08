import pytest

from uv_bundler.domain.platforms import pep508_platform


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


def test_pep508_platform_manylinux2014_x86_64() -> None:
    assert pep508_platform("linux", "x86_64", "2014") == "x86_64-manylinux2014"


def test_pep508_platform_manylinux2014_aarch64() -> None:
    assert pep508_platform("linux", "aarch64", "2014") == "aarch64-manylinux2014"


def test_pep508_platform_manylinux2010() -> None:
    assert pep508_platform("linux", "x86_64", "2010") == "x86_64-manylinux2010"


def test_pep508_platform_manylinux_numeric() -> None:
    # "31" → manylinux_2_31
    assert pep508_platform("linux", "x86_64", "31") == "x86_64-manylinux_2_31"


def test_pep508_platform_no_manylinux_returns_generic() -> None:
    # Without manylinux, fallback to the generic gnu triple
    assert pep508_platform("linux", "x86_64", None) == "x86_64-unknown-linux-gnu"
