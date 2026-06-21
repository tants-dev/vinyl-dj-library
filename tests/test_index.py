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


def test_search_form_handles_enter_key_via_htmx_not_native_submit(session, client):
    # Regression test: the #controls form has hx-get but used to declare an
    # explicit hx-trigger that didn't include "submit". That overrides
    # htmx's default form trigger entirely (rather than adding to it), so
    # pressing Enter fell through to a native browser form submission --
    # a full-page GET to "/" (no action= set) that ignores q/year/genre/
    # artist entirely, which looked like the search being cleared. "submit"
    # must be explicitly listed in hx-trigger for htmx to intercept Enter.
    resp = client.get("/")
    assert 'hx-trigger="input changed delay:200ms from:input[name=\'q\']' in resp.text
    assert "submit" in resp.text.split('hx-trigger="')[1].split('"')[0]


def test_sync_and_enrich_buttons_have_loading_feedback(session, client):
    # Sync/enrich can take 60-90s against a real collection with no visual
    # feedback otherwise -- the button just looks frozen. hx-disabled-elt
    # grays the button out and hx-indicator shows a spinner+text while the
    # request is in flight.
    resp = client.get("/")
    assert 'hx-post="/sync"' in resp.text
    assert 'hx-indicator="#sync-spinner"' in resp.text
    assert 'hx-disabled-elt="this"' in resp.text
    assert 'id="sync-spinner"' in resp.text
    assert 'hx-indicator="#enrich-spinner"' in resp.text
    assert 'id="enrich-spinner"' in resp.text
