from db.models import BpmKeyData, Release, Track


def test_release_detail_shows_tracks(session, client):
    session.add(
        Release(
            id=1,
            title="Test Release",
            artists="Test Artist",
            label="Test Label",
            catalog_number="TL001",
            year=1995,
        )
    )
    session.commit()
    t1 = Track(release_id=1, position="A1", title="Track One")
    t2 = Track(release_id=1, position="A2", title="Track Two")
    session.add(t1)
    session.add(t2)
    session.commit()
    session.refresh(t1)
    session.add(
        BpmKeyData(track_id=t1.id, bpm=140.0, key="F minor", camelot_key="4A", source="manual")
    )
    session.commit()

    resp = client.get("/release/1")

    assert resp.status_code == 200
    assert "Test Release" in resp.text
    assert "Track One" in resp.text
    assert "Track Two" in resp.text
    assert "140" in resp.text
    assert "no BPM/key yet" in resp.text  # Track Two has none


def test_release_not_found_returns_404(session, client):
    resp = client.get("/release/9999")
    assert resp.status_code == 404
