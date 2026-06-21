"""Lets the local server shut itself down from the UI, since this is a
personal local-only tool with no separate process manager (see
docs/DECISIONS.md ADR-001/ADR-004 — no auth, trusted home network only).
"""

import os
import signal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.post("/shutdown", response_class=HTMLResponse)
def shutdown(request: Request):
    os.kill(os.getpid(), signal.SIGTERM)
    return request.app.state.templates.TemplateResponse(
        request, "partials/shutdown.html", {}
    )
