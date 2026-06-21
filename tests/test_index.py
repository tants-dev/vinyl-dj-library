from db.models import BpmKeyData, Release, Track


def test_index_counts_unenriched_tracks(session, client):
    session.add(Release(id=1, title="R", artists="A"))
    session.commit()
    t1 = Track(release_id=1, position="A1", title="Has BPM")
    t2 = Track(release_id=1, position="A2", title="No BPM")
    session.add(t1)
    session.add(t2)
    session.commit()
    session.refresh(t1)
    session.add(BpmKeyData(track_id=t1.id, bpm=128.0, source="manual"))
    session.commit()

    resp = client.get("/")

    assert resp.status_code == 200
    assert "1 track(s) need BPM/key" in resp.text


def test_index_with_empty_db(session, client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "0 track(s) need BPM/key" in resp.text
