from db.models import Track


def _clear_credentials(monkeypatch):
    for var in (
        "DISCOGS_TOKEN",
        "DISCOGS_USERNAME",
        "GETSONGBPM_API_KEY",
        "BEATPORT_CLIENT_ID",
        "BEATPORT_CLIENT_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)


def test_sync_without_credentials_returns_clear_message(session, client, monkeypatch):
    _clear_credentials(monkeypatch)
    resp = client.post("/sync")
    assert resp.status_code == 200
    assert "DISCOGS_TOKEN is not set" in resp.text


def test_enrich_without_sources_configured_is_a_noop(session, client, monkeypatch):
    _clear_credentials(monkeypatch)
    session.add(Track(release_id=1, position="A1", title="Unmatched"))
    session.commit()

    resp = client.post("/enrich")

    assert resp.status_code == 200
    assert "Enriched 0 track(s)" in resp.text
