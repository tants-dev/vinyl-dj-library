def test_tap_bpm_page_loads(client):
    resp = client.get("/tap-bpm")
    assert resp.status_code == 200
    assert "Tap tempo" in resp.text
    assert 'id="tap-bpm-value"' in resp.text
    assert 'id="tap-button"' in resp.text
    assert "Mic-based live analysis coming soon" in resp.text


def test_tap_bpm_nav_link_present_on_every_page(client):
    resp = client.get("/")
    assert 'href="/tap-bpm"' in resp.text
