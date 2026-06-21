from db.models import BpmKeyData, Release, Track


def seed(session):
    release = Release(
        id=1,
        title="Strictly Rhythm Classics",
        artists="Various",
        label="Strictly Rhythm",
        catalog_number="SR12-001",
    )
    session.add(release)
    session.commit()

    track = Track(
        release_id=1,
        position="A1",
        title="Music Is The Answer",
        artists="Aly-Us",
    )
    session.add(track)
    session.commit()
    session.refresh(track)

    session.add(
        BpmKeyData(
            track_id=track.id,
            bpm=124.0,
            key="A minor",
            camelot_key="8A",
            source="manual",
        )
    )
    session.commit()
    return release, track


def test_search_matches_track_title(session, client):
    seed(session)
    resp = client.get("/search", params={"q": "Music Is The Answer"})
    assert resp.status_code == 200
    assert "Music Is The Answer" in resp.text
    assert "124" in resp.text
    assert "8A" in resp.text


def test_search_matches_track_artist(session, client):
    seed(session)
    resp = client.get("/search", params={"q": "Aly-Us"})
    assert "Music Is The Answer" in resp.text


def test_search_matches_release_label(session, client):
    seed(session)
    resp = client.get("/search", params={"q": "Strictly Rhythm"})
    assert "Music Is The Answer" in resp.text


def test_search_matches_catalog_number(session, client):
    seed(session)
    resp = client.get("/search", params={"q": "SR12-001"})
    assert "Music Is The Answer" in resp.text


def test_search_is_case_insensitive(session, client):
    seed(session)
    resp = client.get("/search", params={"q": "aly-us"})
    assert "Music Is The Answer" in resp.text


def test_search_no_match(session, client):
    seed(session)
    resp = client.get("/search", params={"q": "nonexistent track"})
    assert "No matches" in resp.text


def test_search_empty_query_shows_browsable_release_list(session, client):
    seed(session)
    resp = client.get("/search", params={"q": ""})
    assert "Strictly Rhythm Classics" in resp.text
    assert 'href="/release/1"' in resp.text


def test_search_result_links_to_track_not_release(session, client):
    _, track = seed(session)
    resp = client.get("/search", params={"q": "Music Is The Answer"})
    assert f'href="/track/{track.id}"' in resp.text


def test_search_track_without_bpm_key_shows_placeholder(session, client):
    release = Release(id=2, title="White Label", artists="Unknown")
    session.add(release)
    session.commit()
    session.add(Track(release_id=2, position="B1", title="Untitled Dub"))
    session.commit()

    resp = client.get("/search", params={"q": "Untitled Dub"})
    assert "Untitled Dub" in resp.text
    assert "no BPM/key yet" in resp.text
