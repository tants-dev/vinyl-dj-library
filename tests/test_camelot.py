import pytest

from enrich.camelot import _CAMELOT_MAP, to_camelot


def test_known_keys():
    assert to_camelot("C major") == "8B"
    assert to_camelot("A minor") == "8A"
    assert to_camelot("G major") == "9B"
    assert to_camelot("E minor") == "9A"


@pytest.mark.parametrize("key, code", list(_CAMELOT_MAP.items()))
def test_every_mapped_key_round_trips(key, code):
    assert to_camelot(key) == code


def test_strips_whitespace():
    assert to_camelot(" C major ") == "8B"


def test_unknown_key_returns_none():
    assert to_camelot("not a real key") is None


def test_none_input_returns_none():
    assert to_camelot(None) is None


def test_camelot_wheel_is_complete():
    # 12 major + 12 minor keys, each a distinct Camelot code.
    assert len(_CAMELOT_MAP) == 24
    assert len(set(_CAMELOT_MAP.values())) == 24
