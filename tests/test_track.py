from sqlmodel import select

from db.models import BpmKeyData, Release, Track


def make_track(session):
    session.add(Release(id=1, title="Test Release", artists="Test Artist"))
    session.commit()
    track = Track(release_id=1, position="A1", title="Test Track")
    session.add(track)
    session.commit()
    session.refresh(track)
    return track


def test_patch_creates_bpm_key_when_none_exists(session, client):
    track = make_track(session)

    resp = client.patch(
        f"/track/{track.id}/bpm-key", json={"bpm": 128.0, "key": "A minor"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "track_id": track.id,
        "bpm": 128.0,
        "key": "A minor",
        "source": "manual",
    }

    stored = session.get(BpmKeyData, track.id)
    assert stored.bpm == 128.0
    assert stored.key == "A minor"
    assert stored.camelot_key == "8A"
    assert stored.source == "manual"


def test_patch_updates_existing_row_instead_of_duplicating(session, client):
    track = make_track(session)
    session.add(
        BpmKeyData(
            track_id=track.id,
            bpm=120.0,
            key="C major",
            camelot_key="8B",
            source="getsongbpm",
        )
    )
    session.commit()

    resp = client.patch(
        f"/track/{track.id}/bpm-key", json={"bpm": 130.5, "key": "G major"}
    )
    assert resp.status_code == 200

    rows = session.exec(
        select(BpmKeyData).where(BpmKeyData.track_id == track.id)
    ).all()
    assert len(rows) == 1

    stored = session.get(BpmKeyData, track.id)
    assert stored.bpm == 130.5
    assert stored.key == "G major"
    assert stored.camelot_key == "9B"
    assert stored.source == "manual"


def test_patch_unknown_track_returns_404(session, client):
    resp = client.patch("/track/9999/bpm-key", json={"bpm": 128.0, "key": "A minor"})
    assert resp.status_code == 404


def test_patch_with_unrecognized_key_stores_null_camelot(session, client):
    track = make_track(session)
    resp = client.patch(
        f"/track/{track.id}/bpm-key", json={"bpm": 128.0, "key": "not a real key"}
    )
    assert resp.status_code == 200
    assert resp.json()["key"] == "not a real key"

    stored = session.get(BpmKeyData, track.id)
    assert stored.camelot_key is None


def test_patch_from_htmx_returns_html_partial_not_json(session, client):
    track = make_track(session)

    resp = client.patch(
        f"/track/{track.id}/bpm-key",
        json={"bpm": 128.0, "key": "A minor"},
        headers={"HX-Request": "true"},
    )

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "128" in resp.text
    assert "8A" in resp.text
    assert f'id="bpm-key-{track.id}"' in resp.text
    assert "manual" in resp.text
