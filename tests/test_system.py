import os
import signal


def test_shutdown_signals_own_process_without_actually_killing_it(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "api.routes.system.os.kill", lambda pid, sig: calls.append((pid, sig))
    )

    resp = client.post("/shutdown")

    assert resp.status_code == 200
    assert "Server stopped" in resp.text
    assert calls == [(os.getpid(), signal.SIGTERM)]
