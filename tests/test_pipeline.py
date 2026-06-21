import httpx

from db.models import BpmKeyData, Release, Track
from enrich import pipeline


class _FakeSource:
    __name__ = "fake_source"

    def __init__(self, configured, behavior):
        self._configured = configured
        self._behavior = behavior

    def is_configured(self):
        return self._configured

    def lookup(self, artist, title):
        return self._behavior(artist, title)


def _seed_track(session):
    session.add(Release(id=1, title="R", artists="A"))
    session.commit()
    track = Track(release_id=1, position="A1", title="Some Track")
    session.add(track)
    session.commit()
    session.refresh(track)
    return track


def test_a_failing_source_does_not_abort_the_whole_track(session, monkeypatch):
    track = _seed_track(session)

    def raise_http_error(artist, title):
        raise httpx.HTTPError("boom")

    def succeed(artist, title):
        from enrich.sources.base import Match

        return Match(bpm=128.0, key="A minor", source="fake_source_2")

    failing = _FakeSource(configured=True, behavior=raise_http_error)
    working = _FakeSource(configured=True, behavior=succeed)
    monkeypatch.setattr(pipeline, "SOURCES_IN_PRIORITY_ORDER", [failing, working])

    enriched = pipeline.enrich_unmatched_tracks(session)

    assert enriched == 1
    stored = session.get(BpmKeyData, track.id)
    assert stored.bpm == 128.0
    assert stored.source == "fake_source_2"
    assert stored.camelot_key == "8A"


def test_a_failing_source_does_not_crash_when_no_fallback_matches(session, monkeypatch):
    _seed_track(session)

    def raise_http_error(artist, title):
        raise httpx.HTTPError("boom")

    failing = _FakeSource(configured=True, behavior=raise_http_error)
    monkeypatch.setattr(pipeline, "SOURCES_IN_PRIORITY_ORDER", [failing])

    enriched = pipeline.enrich_unmatched_tracks(session)

    assert enriched == 0


def test_no_configured_sources_enriches_nothing(session, monkeypatch):
    _seed_track(session)
    unconfigured = _FakeSource(configured=False, behavior=lambda a, t: None)
    monkeypatch.setattr(pipeline, "SOURCES_IN_PRIORITY_ORDER", [unconfigured])

    assert pipeline.enrich_unmatched_tracks(session) == 0


def test_falls_back_to_release_artist_when_track_has_none(session, monkeypatch):
    # Regression test: most vinyl isn't a various-artists compilation, so
    # Track.artists is None and the real credit only lives on the release
    # (see api/routes/search.py, which already falls back this way for
    # display). The pipeline used to pass an empty string in this case,
    # silently failing every lookup against the real GetSongBPM API even
    # though the artist was known via the release.
    session.add(Release(id=99, title="Some Release", artists="The Real Artist"))
    session.commit()
    track = Track(release_id=99, position="A1", title="Some Track")
    session.add(track)
    session.commit()
    session.refresh(track)

    captured_artist = {}

    def capture(artist, title):
        from enrich.sources.base import Match

        captured_artist["value"] = artist
        return Match(bpm=120.0, key="C major", source="fake_source")

    source = _FakeSource(configured=True, behavior=capture)
    monkeypatch.setattr(pipeline, "SOURCES_IN_PRIORITY_ORDER", [source])

    pipeline.enrich_unmatched_tracks(session)

    assert captured_artist["value"] == "The Real Artist"


def test_uses_track_artist_over_release_artist_when_both_present(session, monkeypatch):
    # Compilation case: a track can have its own distinct artist credit.
    session.add(Release(id=98, title="Various Artists Comp", artists="Various"))
    session.commit()
    track = Track(
        release_id=98, position="A1", title="Some Track", artists="The Track Artist"
    )
    session.add(track)
    session.commit()
    session.refresh(track)

    captured_artist = {}

    def capture(artist, title):
        from enrich.sources.base import Match

        captured_artist["value"] = artist
        return Match(bpm=120.0, key="C major", source="fake_source")

    source = _FakeSource(configured=True, behavior=capture)
    monkeypatch.setattr(pipeline, "SOURCES_IN_PRIORITY_ORDER", [source])

    pipeline.enrich_unmatched_tracks(session)

    assert captured_artist["value"] == "The Track Artist"
