import httpx
import pytest

from enrich.camelot import to_camelot
from enrich.sources import getsongbpm
from enrich.sources.getsongbpm import _parse_key_of


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


def test_is_configured_reflects_env_var(monkeypatch):
    monkeypatch.delenv("GETSONGBPM_API_KEY", raising=False)
    assert getsongbpm.is_configured() is False

    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    assert getsongbpm.is_configured() is True


def test_lookup_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("GETSONGBPM_API_KEY", raising=False)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not call the API without a key")

    monkeypatch.setattr(httpx, "get", fail_if_called)
    assert getsongbpm.lookup("Aly-Us", "Follow Me") is None


def test_lookup_returns_match_on_success(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(
            {
                "search": [
                    {"id": "xyz", "title": "Follow Me", "tempo": "124", "key_of": "Am"}
                ]
            }
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    match = getsongbpm.lookup("Aly-Us", "Follow Me")

    assert match.bpm == 124.0
    assert match.key == "A minor"
    assert match.source == "getsongbpm"
    assert captured["url"] == f"{getsongbpm.API_BASE}/search/"
    assert captured["params"]["api_key"] == "abc123"
    assert captured["params"]["type"] == "song"
    assert captured["params"]["lookup"] == "song:Follow Me artist:Aly-Us"


def test_lookup_handles_string_no_results_response(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse({"search": "No Results"})
    )
    assert getsongbpm.lookup("Nobody", "Nothing") is None


def test_lookup_handles_empty_results_list(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse({"search": []}))
    assert getsongbpm.lookup("Nobody", "Nothing") is None


def test_lookup_returns_none_when_result_has_no_usable_data(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: FakeResponse({"search": [{"id": "xyz", "title": "T"}]}),
    )
    assert getsongbpm.lookup("A", "T") is None


def test_lookup_raises_on_http_error_status(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "bad-key")
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse({}, status_code=401)
    )
    with pytest.raises(httpx.HTTPStatusError):
        getsongbpm.lookup("A", "T")


@pytest.mark.parametrize(
    "key_of, expected",
    [
        ("C", "C major"),
        ("Am", "A minor"),
        ("C#", "Db major"),
        ("C#m", "C# minor"),
        ("Db", "Db major"),
        ("Dbm", "C# minor"),
        ("Gb", "F# major"),
        ("Gbm", "F# minor"),
        ("Bbm", "Bb minor"),
        ("A#", "Bb major"),
        ("", None),
        (None, None),
        ("Hm", None),  # not a real note
    ],
)
def test_parse_key_of(key_of, expected):
    assert _parse_key_of(key_of) == expected


@pytest.mark.parametrize(
    "key_of",
    ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A",
     "A#", "Bb", "B",
     "Cm", "C#m", "Dbm", "Dm", "D#m", "Ebm", "Em", "Fm", "F#m", "Gbm", "Gm", "G#m",
     "Abm", "Am", "A#m", "Bbm", "Bm"],
)
def test_every_parsed_key_resolves_to_a_real_camelot_code(key_of):
    parsed = _parse_key_of(key_of)
    assert parsed is not None
    assert to_camelot(parsed) is not None
