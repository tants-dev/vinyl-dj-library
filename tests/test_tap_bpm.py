from db.models import BpmKeyData, Release, Track


def _seed_track(session, *, cover_image_url=None, bpm=None, key=None):
    r = Release(id=1, title="Born Slippy", artists="Underworld", cover_image_url=cover_image_url)
    session.add(r)
    session.commit()
    t = Track(release_id=1, position="A1", title="Born Slippy .Nuxx")
    session.add(t)
    session.commit()
    session.refresh(t)
    if bpm is not None:
        session.add(BpmKeyData(track_id=t.id, bpm=bpm, key=key, camelot_key="8A", source="getsongbpm"))
        session.commit()
    return t


# ── no-track page (general mode) ─────────────────────────────────────────────

def test_tap_bpm_page_loads_without_track(client):
    resp = client.get("/tap-bpm")
    assert resp.status_code == 200


def test_tap_bpm_page_has_record_clip_section(client):
    resp = client.get("/tap-bpm")
    assert 'id="clip-record-btn"' in resp.text
    assert 'id="clip-result"' in resp.text


def test_tap_bpm_page_has_tap_tempo_section(client):
    resp = client.get("/tap-bpm")
    assert 'id="tap-bpm-value"' in resp.text
    assert 'id="tap-button"' in resp.text
    assert 'id="tap-use-btn"' in resp.text


def test_tap_bpm_page_has_shared_save_section(client):
    resp = client.get("/tap-bpm")
    assert 'id="save-bpm-input"' in resp.text
    assert 'id="save-key-input"' in resp.text
    assert 'id="clip-track-search"' in resp.text


def test_tap_bpm_page_without_track_shows_search_not_preset_save(client):
    resp = client.get("/tap-bpm")
    # No preset track → no preset save block
    assert 'id="clip-preset-btn"' not in resp.text
    assert "Save to track:" in resp.text


# ── nav link ─────────────────────────────────────────────────────────────────

def test_tap_bpm_nav_link_present_on_every_page(client):
    resp = client.get("/")
    assert 'href="/tap-bpm"' in resp.text


def test_nav_link_says_analyse(client):
    resp = client.get("/")
    assert ">Analyse<" in resp.text


# ── ?track_id= (preset track mode) ───────────────────────────────────────────

def test_tap_bpm_with_track_id_shows_now_analysing_header(session, client):
    t = _seed_track(session)
    resp = client.get(f"/tap-bpm?track_id={t.id}")
    assert resp.status_code == 200
    assert "NOW ANALYSING" in resp.text.upper()
    assert "Born Slippy .Nuxx" in resp.text
    assert "Underworld" in resp.text


def test_tap_bpm_with_track_id_shows_preset_save_button(session, client):
    t = _seed_track(session)
    resp = client.get(f"/tap-bpm?track_id={t.id}")
    assert 'id="clip-preset-btn"' in resp.text
    # Should also show "Or save to a different track" search
    assert "Or save to a different track:" in resp.text


def test_tap_bpm_with_track_id_passes_preset_data_to_js(session, client):
    t = _seed_track(session)
    resp = client.get(f"/tap-bpm?track_id={t.id}")
    # Hidden element carries track data for JS
    assert 'id="clip-preset-track"' in resp.text
    assert f'data-id="{t.id}"' in resp.text


def test_tap_bpm_with_track_id_shows_cover_art(session, client):
    t = _seed_track(session, cover_image_url="https://example.com/cover.jpg")
    resp = client.get(f"/tap-bpm?track_id={t.id}")
    assert 'class="analysing-art"' in resp.text
    assert "https://example.com/cover.jpg" in resp.text


def test_tap_bpm_without_cover_art_omits_img_tag(session, client):
    t = _seed_track(session, cover_image_url=None)
    resp = client.get(f"/tap-bpm?track_id={t.id}")
    assert 'class="analysing-art"' not in resp.text


def test_tap_bpm_with_existing_bpm_shows_currently_saved(session, client):
    t = _seed_track(session, bpm=130.0, key="A minor")
    resp = client.get(f"/tap-bpm?track_id={t.id}")
    assert "Currently saved" in resp.text
    assert "130" in resp.text


def test_tap_bpm_without_existing_bpm_omits_currently_saved(session, client):
    t = _seed_track(session)
    resp = client.get(f"/tap-bpm?track_id={t.id}")
    assert "Currently saved" not in resp.text


def test_tap_bpm_invalid_track_id_falls_back_to_no_preset(client):
    resp = client.get("/tap-bpm?track_id=9999")
    assert resp.status_code == 200
    assert "NOW ANALYSING" not in resp.text.upper()
    assert 'id="clip-preset-btn"' not in resp.text
