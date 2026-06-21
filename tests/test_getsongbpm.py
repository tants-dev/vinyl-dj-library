import httpx
import pytest

from enrich.camelot import to_camelot
from enrich.sources import getsongbpm
from enrich.sources.getsongbpm import _artist_matches, _parse_key_of


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


def _song(artist, title="Levels", tempo="124", key_of="Am"):
    return {
        "id": "xyz",
        "title": title,
        "tempo": tempo,
        "key_of": key_of,
        "artist": {"name": artist},
    }


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


def test_lookup_searches_by_title_only(monkeypatch):
    # The live API ignores artist filtering server-side (confirmed against
    # the real endpoint) — searches must be title-only, with the right
    # artist picked out of the results client-side.
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse({"search": [_song("Aly-Us", "Follow Me")]})

    monkeypatch.setattr(httpx, "get", fake_get)
    getsongbpm.lookup("Aly-Us", "Follow Me")

    assert captured["url"] == f"{getsongbpm.API_BASE}/search/"
    assert captured["params"] == {
        "api_key": "abc123",
        "type": "song",
        "lookup": "Follow Me",
    }


def test_lookup_picks_the_matching_artist_out_of_several_results(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: FakeResponse(
            {
                "search": [
                    _song("Nonpoint", tempo="100", key_of="C♯"),
                    _song("Gunplay", tempo="73", key_of="A"),
                    _song("Avicii", tempo="126", key_of="Cm"),
                ]
            }
        ),
    )

    match = getsongbpm.lookup("Avicii", "Levels")

    assert match.bpm == 126.0
    assert match.key == "C minor"
    assert match.source == "getsongbpm"


def test_lookup_returns_none_when_artist_not_among_results(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: FakeResponse({"search": [_song("Nonpoint"), _song("Gunplay")]}),
    )
    assert getsongbpm.lookup("Avicii", "Levels") is None


def test_lookup_handles_dict_no_results_response(monkeypatch):
    # Confirmed against the live API: a miss looks like
    # {"search": {"error": "no result"}} — a dict, not an empty list.
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse({"search": {"error": "no result"}})
    )
    assert getsongbpm.lookup("Nobody", "Nothing") is None


def test_lookup_handles_empty_results_list(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse({"search": []}))
    assert getsongbpm.lookup("Nobody", "Nothing") is None


def test_lookup_returns_none_when_match_has_no_usable_data(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "abc123")
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: FakeResponse(
            {"search": [{"id": "xyz", "title": "T", "artist": {"name": "A"}}]}
        ),
    )
    assert getsongbpm.lookup("A", "T") is None


def test_lookup_raises_on_http_error_status(monkeypatch):
    monkeypatch.setenv("GETSONGBPM_API_KEY", "bad-key")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse({}, status_code=401))
    with pytest.raises(httpx.HTTPStatusError):
        getsongbpm.lookup("A", "T")


@pytest.mark.parametrize(
    "wanted, candidate, expected",
    [
        ("Avicii", "Avicii", True),
        ("avicii", "Avicii", True),
        (" Avicii ", "Avicii", True),
        ("Daft Punk", "Daft  Punk", True),  # extra internal whitespace
        ("Air", "Fairground Attraction", False),  # substring false positive
        ("Avicii", "Nonpoint", False),
        ("", "Avicii", False),
    ],
)
def test_artist_matches(wanted, candidate, expected):
    assert _artist_matches(wanted, candidate) is expected


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
        # The live API uses the unicode sharp sign, not ASCII '#'.
        ("C♯", "Db major"),
        ("G♯m", "G# minor"),
        ("", None),
        (None, None),
        ("Hm", None),  # not a real note
        ("m", None),  # seen in real responses for tracks with no known key
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
