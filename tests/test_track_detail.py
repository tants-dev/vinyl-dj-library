import re

from db.models import BpmKeyData, Release, Track


def _seed(session):
    session.add(
        Release(
            id=1,
            title="Strobe",
            artists="deadmau5",
            label="mau5trap",
            catalog_number="MAU5-001",
            year=2009,
            format="Vinyl",
            genres="Electronic, Progressive House",
            styles="Progressive House",
        )
    )
    session.commit()
    t1 = Track(release_id=1, position="A1", title="Strobe")
    t2 = Track(release_id=1, position="B1", title="Ghosts n Stuff")
    session.add(t1)
    session.add(t2)
    session.commit()
    session.refresh(t1)
    session.add(BpmKeyData(track_id=t1.id, bpm=128.0, key="G# minor", camelot_key="1A", source="manual"))
    session.commit()
    return t1, t2


def test_track_detail_shows_featured_track_and_full_release(session, client):
    t1, t2 = _seed(session)

    resp = client.get(f"/track/{t1.id}")

    assert resp.status_code == 200
    assert "featured-track" in resp.text
    assert "Strobe" in resp.text
    assert "128" in resp.text
    # Full release tracklist appears underneath, including the other track.
    assert "Ghosts n Stuff" in resp.text
    assert "Electronic, Progressive House" in resp.text


def test_track_detail_has_manual_entry_form_at_the_top(session, client):
    t1, _ = _seed(session)
    resp = client.get(f"/track/{t1.id}")

    featured_index = resp.text.index("featured-track")
    form_index = resp.text.index("edit-form")
    assert form_index > featured_index
    # The edit form should appear before the "Full release" section heading.
    full_release_index = resp.text.index("Full release")
    assert form_index < full_release_index


def test_track_detail_bpm_key_id_not_duplicated(session, client):
    # The featured track also appears in the full tracklist below; only the
    # featured (editable) instance should carry the DOM id, to avoid an
    # invalid duplicate id and ambiguous htmx hx-target resolution.
    t1, _ = _seed(session)
    resp = client.get(f"/track/{t1.id}")

    assert resp.text.count(f'id="bpm-key-{t1.id}"') == 1


def test_track_detail_no_info_is_clickable_except_back_link(session, client):
    t1, _ = _seed(session)
    resp = client.get(f"/track/{t1.id}")

    anchors = re.findall(r"<a\b", resp.text)
    assert len(anchors) == 1  # only "back to search"


def test_track_detail_not_found_returns_404(session, client):
    resp = client.get("/track/9999")
    assert resp.status_code == 404
