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
