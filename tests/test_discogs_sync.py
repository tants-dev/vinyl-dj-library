import httpx
import pytest
from sqlmodel import select

from db.models import BpmKeyData, Release, Track
from sync import discogs_sync
from sync.discogs_sync import _join_artist_credits, sync_collection


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


def _collection_page(release_ids, page=1, pages=1):
    return FakeResponse(
        {
            "pagination": {"page": page, "pages": pages},
            "releases": [{"id": rid} for rid in release_ids],
        }
    )


def _release_detail(
    release_id,
    title="Strobe",
    artists_sort="deadmau5",
    tracklist=None,
):
    return FakeResponse(
        {
            "id": release_id,
            "title": title,
            "artists_sort": artists_sort,
            "artists": [{"name": artists_sort, "join": ""}],
            "labels": [{"name": "mau5trap", "catno": "MAU5-001"}],
            "year": 2009,
            "formats": [{"name": "Vinyl"}],
            "genres": ["Electronic"],
            "styles": ["Progressive House"],
            "images": [{"uri": "https://example.com/cover.jpg"}],
            "tracklist": tracklist
            if tracklist is not None
            else [
                {"position": "A1", "type_": "track", "title": "Strobe", "duration": "10:33"},
                {"position": "B1", "type_": "track", "title": "Ghosts n Stuff", "duration": "5:46"},
            ],
        }
    )


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    monkeypatch.setattr(discogs_sync.time, "sleep", lambda seconds: None)


@pytest.fixture(autouse=True)
def _credentials(monkeypatch):
    monkeypatch.setenv("DISCOGS_TOKEN", "fake-token")
    monkeypatch.setenv("DISCOGS_USERNAME", "fake-user")
    monkeypatch.setenv("DISCOGS_COLLECTION_FOLDER_ID", "0")


def test_missing_credentials_raises_clear_error(session, monkeypatch):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="DISCOGS_TOKEN"):
        sync_collection(session)


def test_sync_creates_release_and_tracks(session, monkeypatch):
    responses = iter([_collection_page([123]), _release_detail(123)])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(responses))

    count = sync_collection(session)

    assert count == 1
    release = session.get(Release, 123)
    assert release.title == "Strobe"
    assert release.artists == "deadmau5"
    assert release.label == "mau5trap"
    assert release.catalog_number == "MAU5-001"
    assert release.year == 2009
    assert release.format == "Vinyl"
    assert release.genres == "Electronic"
    assert release.styles == "Progressive House"
    assert release.cover_image_url == "https://example.com/cover.jpg"
    assert release.discogs_synced_at is not None


def test_sync_paginates_collection_listing(session, monkeypatch):
    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append((url, params))
        if "collection/folders" in url:
            page = params["page"]
            if page == 1:
                return _collection_page([1], page=1, pages=2)
            return _collection_page([2], page=2, pages=2)
        release_id = int(url.rsplit("/", 1)[-1])
        return _release_detail(release_id)

    monkeypatch.setattr(httpx, "get", fake_get)

    count = sync_collection(session)

    assert count == 2
    assert session.get(Release, 1) is not None
    assert session.get(Release, 2) is not None


def test_sync_skips_non_track_tracklist_entries(session, monkeypatch):
    tracklist = [
        {"position": "", "type_": "heading", "title": "Side A"},
        {"position": "A1", "type_": "track", "title": "Strobe", "duration": "10:33"},
    ]
    responses = iter([_collection_page([123]), _release_detail(123, tracklist=tracklist)])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(responses))

    sync_collection(session)

    tracks = session.exec(select(Track).where(Track.release_id == 123)).all()
    assert len(tracks) == 1
    assert tracks[0].position == "A1"


def test_resyncing_preserves_track_id_and_does_not_orphan_bpm_key_data(
    session, monkeypatch
):
    # First sync.
    responses = iter([_collection_page([123]), _release_detail(123)])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(responses))
    sync_collection(session)

    track = session.exec(
        select(Track).where(Track.release_id == 123, Track.position == "A1")
    ).one()
    original_track_id = track.id

    # Manually enrich it, the way a user would via the UI.
    session.add(
        BpmKeyData(track_id=original_track_id, bpm=128.0, key="A minor", source="manual")
    )
    session.commit()

    # Re-sync the same release (e.g. user clicked Sync again).
    responses = iter([_collection_page([123]), _release_detail(123)])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(responses))
    sync_collection(session)

    track_after = session.exec(
        select(Track).where(Track.release_id == 123, Track.position == "A1")
    ).one()
    assert track_after.id == original_track_id

    bpm_key = session.get(BpmKeyData, original_track_id)
    assert bpm_key is not None
    assert bpm_key.bpm == 128.0
    assert bpm_key.source == "manual"


def test_resyncing_updates_changed_release_fields_in_place(session, monkeypatch):
    responses = iter([_collection_page([123]), _release_detail(123, title="Old Title")])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(responses))
    sync_collection(session)
    assert session.get(Release, 123).title == "Old Title"

    responses = iter([_collection_page([123]), _release_detail(123, title="New Title")])
    monkeypatch.setattr(httpx, "get", lambda *a, **k: next(responses))
    sync_collection(session)

    assert session.get(Release, 123).title == "New Title"

    assert len(session.exec(select(Release).where(Release.id == 123)).all()) == 1


def test_sync_raises_on_http_error(session, monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse({}, status_code=500)
    )
    with pytest.raises(httpx.HTTPStatusError):
        sync_collection(session)


@pytest.mark.parametrize(
    "artists, expected",
    [
        (None, None),
        ([], None),
        ([{"name": "deadmau5", "join": ""}], "deadmau5"),
        # The following are verified against real artists_sort values from
        # the live Discogs API, not guessed.
        (
            [{"name": "Overmono", "join": "&"}, {"name": "High Contrast", "join": ""}],
            "Overmono & High Contrast",
        ),
        (
            [{"name": "Ben Böhmer", "join": "Feat."}, {"name": "Felix Raphael", "join": ""}],
            "Ben Böhmer Feat. Felix Raphael",
        ),
        (
            # Comma gets no leading space, unlike every other join type.
            [{"name": "Prozak (11)", "join": ","}, {"name": "Silva Bumpa", "join": ""}],
            "Prozak (11), Silva Bumpa",
        ),
        (
            # Discogs' own disambiguation suffixes ("(3)", "(4)") are kept
            # as-is, not stripped — artists_sort keeps them too.
            [
                {"name": "Natty (3)", "join": "X"},
                {"name": "Mala (4)", "join": "XX"},
                {"name": "Benjamin Zephaniah", "join": ""},
            ],
            "Natty (3) X Mala (4) XX Benjamin Zephaniah",
        ),
    ],
)
def test_join_artist_credits(artists, expected):
    assert _join_artist_credits(artists) == expected
