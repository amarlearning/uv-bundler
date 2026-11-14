import pytest

from uv_bundler.domain.platforms import pep508_platform, wheel_platform_tag


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


@pytest.mark.parametrize(
    ("platform", "arch", "manylinux", "expected"),
    [
        ("linux", "x86_64", None, "manylinux2014_x86_64"),
        ("linux", "aarch64", "2010", "manylinux2010_aarch64"),
        ("linux", "x86_64", "31", "manylinux_2_31_x86_64"),
        ("macos", "x86_64", None, "macosx_10_9_x86_64"),
        ("macos", "aarch64", None, "macosx_11_0_arm64"),
        ("windows", "x86_64", None, "win_amd64"),
        ("windows", "aarch64", None, "win_arm64"),
    ],
)
def test_wheel_platform_tag(platform: str, arch: str, manylinux: str | None, expected: str) -> None:
    assert wheel_platform_tag(platform, arch, manylinux) == expected


def test_wheel_platform_tag_unknown_platform_raises() -> None:
    with pytest.raises(ValueError):
        wheel_platform_tag("plan9", "x86_64")
