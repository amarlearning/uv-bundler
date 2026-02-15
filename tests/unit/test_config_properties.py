import string

import pytest
from hypothesis import given
from hypothesis import strategies as st

from uv_pack.domain.config import TargetConfig


def valid_module_strategy() -> st.SearchStrategy[str]:
    first = st.sampled_from(string.ascii_letters + "_")
    rest = st.text(string.ascii_letters + string.digits + "_", min_size=0, max_size=10)
    part = st.builds(str.__add__, first, rest)
    return st.lists(part, min_size=1, max_size=3).map(".".join)


def valid_function_strategy() -> st.SearchStrategy[str]:
    first = st.sampled_from(string.ascii_letters + "_")
    rest = st.text(string.ascii_letters + string.digits + "_", min_size=0, max_size=10)
    return st.builds(str.__add__, first, rest)


@given(
    st.builds(
        lambda m, f: f"{m}:{f}",
        valid_module_strategy(),
        valid_function_strategy(),
    )
)
def test_target_config_accepts_valid_entry_points(entry_point: str) -> None:
    cfg = TargetConfig(entry_point=entry_point)
    assert cfg.entry_point == entry_point


@given(
    st.text(min_size=1, max_size=20).filter(
        lambda s: ":" not in s or s.startswith(":") or s.endswith(":")
    )
)
def test_target_config_rejects_invalid_entry_points(entry_point: str) -> None:
    with pytest.raises(ValueError):
        TargetConfig(entry_point=entry_point)
