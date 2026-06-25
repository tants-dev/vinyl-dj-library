import io
from unittest.mock import patch

from db.models import BpmKeyData, Release, Track
from enrich.sources.base import Match


# ── helpers ───────────────────────────────────────────────────────────────────

def _seed(session, *, release_kwargs=None, tracks=None):
    rk = {"id": 1, "title": "Test Release", "artists": "Test Artist", **(release_kwargs or {})}
    r = Release(**rk)
    session.add(r)
    session.commit()
    added = []
    for i, tkw in enumerate(tracks or []):
        t = Track(release_id=r.id, position=f"A{i + 1}", **tkw)
        session.add(t)
        session.commit()
        session.refresh(t)
        added.append(t)
    return r, added


# Minimal valid WAV header (0-byte data chunk) — enough for the route to
# accept the upload without calling the real librosa, since we patch it.
_EMPTY_WAV = (
    b"RIFF$\x00\x00\x00"   # RIFF chunk, total size 36
    b"WAVE"
    b"fmt \x10\x00\x00\x00"  # fmt chunk, 16 bytes
    b"\x01\x00"              # PCM
    b"\x01\x00"              # mono
    b"\x44\xac\x00\x00"      # 44100 Hz
    b"\x88\x58\x01\x00"      # byte rate
    b"\x02\x00"              # block align
    b"\x10\x00"              # 16-bit
    b"data\x00\x00\x00\x00"  # data chunk, 0 bytes
)


# ── GET /track-search ─────────────────────────────────────────────────────────

def test_track_search_empty_query_returns_empty(client):
    resp = client.get("/track-search?q=")
    assert resp.status_code == 200
    assert resp.json() == []


def test_track_search_no_match_returns_empty(session, client):
    _seed(session, tracks=[{"title": "Some Track"}])
    assert client.get("/track-search?q=xyznothing").json() == []


def test_track_search_matches_by_track_title(session, client):
    _seed(session, tracks=[{"title": "Born Slippy"}])
    results = client.get("/track-search?q=slippy").json()
    assert len(results) == 1
    assert results[0]["title"] == "Born Slippy"


def test_track_search_matches_by_track_artist(session, client):
    _seed(session, tracks=[{"title": "Acperience 1", "artists": "Hardfloor"}])
    results = client.get("/track-search?q=hardfloor").json()
    assert results[0]["title"] == "Acperience 1"


def test_track_search_matches_by_release_artist(session, client):
    _seed(
        session,
        release_kwargs={"artists": "Underworld"},
        tracks=[{"title": "Dark & Long"}],
    )
    results = client.get("/track-search?q=underworld").json()
    assert results[0]["title"] == "Dark & Long"


def test_track_search_matches_by_release_title(session, client):
    _seed(
        session,
        release_kwargs={"title": "Dubnobasswithmyheadman"},
        tracks=[{"title": "Dark & Long"}],
    )
    results = client.get("/track-search?q=dubno").json()
    assert results[0]["title"] == "Dark & Long"


def test_track_search_is_case_insensitive(session, client):
    _seed(session, tracks=[{"title": "BORN SLIPPY"}])
    assert len(client.get("/track-search?q=born slippy").json()) == 1


def test_track_search_title_ranked_before_artist(session, client):
    """A title match should sort above an artist-only match."""
    r1 = Release(id=1, title="Album A", artists="Leftfield")
    r2 = Release(id=2, title="Album B", artists="Leftfield")
    session.add_all([r1, r2])
    session.commit()
    by_title  = Track(release_id=1, position="A1", title="Leftfield Song")
    by_artist = Track(release_id=2, position="A1", title="Something Else")
    session.add_all([by_title, by_artist])
    session.commit()

    results = client.get("/track-search?q=leftfield").json()
    assert len(results) == 2
    assert results[0]["title"] == "Leftfield Song"


def test_track_search_artist_ranked_before_release_title(session, client):
    """An artist match should sort above a release-title-only match."""
    r1 = Release(id=1, title="Plastic", artists="Plastikman")   # artist match
    r2 = Release(id=2, title="Plastikman Remixes", artists="VA") # release-title match
    session.add_all([r1, r2])
    session.commit()
    by_artist  = Track(release_id=1, position="A1", title="Spastik")
    by_release = Track(release_id=2, position="A1", title="Some Remix")
    session.add_all([by_artist, by_release])
    session.commit()

    results = client.get("/track-search?q=plastikman").json()
    assert len(results) == 2
    assert results[0]["title"] == "Spastik"


def test_track_search_includes_existing_bpm_and_camelot_key(session, client):
    _, tracks = _seed(session, tracks=[{"title": "Test Track"}])
    session.add(BpmKeyData(
        track_id=tracks[0].id, bpm=130.0, key="A minor", camelot_key="8A", source="getsongbpm"
    ))
    session.commit()

    result = client.get("/track-search?q=test").json()[0]
    assert result["existing_bpm"] == 130.0
    assert result["existing_key"] == "8A"   # camelot_key preferred


def test_track_search_falls_back_to_key_when_no_camelot(session, client):
    _, tracks = _seed(session, tracks=[{"title": "Test Track"}])
    session.add(BpmKeyData(
        track_id=tracks[0].id, bpm=130.0, key="A minor", camelot_key=None, source="manual"
    ))
    session.commit()

    result = client.get("/track-search?q=test").json()[0]
    assert result["existing_key"] == "A minor"


def test_track_search_existing_fields_none_without_bpm_data(session, client):
    _seed(session, tracks=[{"title": "Mystery Track"}])
    result = client.get("/track-search?q=mystery").json()[0]
    assert result["existing_bpm"] is None
    assert result["existing_key"] is None


def test_track_search_response_shape(session, client):
    """Every result contains the fields the JS save flow depends on."""
    _seed(session, tracks=[{"title": "Shape Check"}])
    result = client.get("/track-search?q=shape").json()[0]
    assert set(result.keys()) == {"id", "title", "artist", "release", "existing_bpm", "existing_key"}


def test_track_search_limit_ten_results(session, client):
    r = Release(id=1, title="Various", artists="VA")
    session.add(r)
    session.commit()
    for i in range(15):
        session.add(Track(release_id=1, position=f"A{i+1}", title=f"Track {i+1}"))
    session.commit()
    # All 15 titles contain "Track", but the endpoint limits to 10.
    results = client.get("/track-search?q=track").json()
    assert len(results) <= 10


# ── POST /analyze-clip ────────────────────────────────────────────────────────

def test_analyze_clip_returns_bpm_key_camelot_confidence(client):
    fake = Match(bpm=128.0, key="A minor", source="local_analysis", confidence=0.72)
    with patch("api.routes.analyze.analyze_sample", return_value=fake):
        resp = client.post(
            "/analyze-clip",
            files={"file": ("clip.wav", io.BytesIO(_EMPTY_WAV), "audio/wav")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["bpm"] == 128.0
    assert body["key"] == "A minor"
    assert body["camelot"] == "8A"
    assert body["confidence"] == 0.72


def test_analyze_clip_camelot_derived_from_key(client):
    fake = Match(bpm=135.0, key="G major", source="local_analysis", confidence=0.65)
    with patch("api.routes.analyze.analyze_sample", return_value=fake):
        resp = client.post(
            "/analyze-clip",
            files={"file": ("clip.wav", io.BytesIO(_EMPTY_WAV), "audio/wav")},
        )
    assert resp.json()["camelot"] == "9B"


def test_analyze_clip_unknown_key_gives_null_camelot(client):
    fake = Match(bpm=120.0, key="something weird", source="local_analysis", confidence=0.3)
    with patch("api.routes.analyze.analyze_sample", return_value=fake):
        resp = client.post(
            "/analyze-clip",
            files={"file": ("clip.wav", io.BytesIO(_EMPTY_WAV), "audio/wav")},
        )
    body = resp.json()
    assert body["key"] == "something weird"
    assert body["camelot"] is None


def test_analyze_clip_returns_503_when_librosa_missing(client):
    with patch(
        "api.routes.analyze.analyze_sample",
        side_effect=RuntimeError("librosa is not installed"),
    ):
        resp = client.post(
            "/analyze-clip",
            files={"file": ("clip.wav", io.BytesIO(_EMPTY_WAV), "audio/wav")},
        )
    assert resp.status_code == 503
    assert "librosa" in resp.json()["detail"]


def test_analyze_clip_returns_422_on_analysis_failure(client):
    with patch(
        "api.routes.analyze.analyze_sample",
        side_effect=Exception("corrupt audio"),
    ):
        resp = client.post(
            "/analyze-clip",
            files={"file": ("clip.wav", io.BytesIO(_EMPTY_WAV), "audio/wav")},
        )
    assert resp.status_code == 422
