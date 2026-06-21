"""Beatport API adapter — primary BPM/key source for electronic music.

Partner-gated API; requires BEATPORT_CLIENT_ID/SECRET (see docs/DECISIONS.md
ADR-003's open risk). Not yet implemented pending partner approval.
"""

import os
from typing import Optional

from enrich.sources.base import Match


def is_configured() -> bool:
    return bool(os.environ.get("BEATPORT_CLIENT_ID")) and bool(
        os.environ.get("BEATPORT_CLIENT_SECRET")
    )


def lookup(artist: str, title: str) -> Optional[Match]:
    if not is_configured():
        return None
    # TODO (Phase 2): OAuth2 client-credentials flow, then search by
    # artist + title (+ catalog number if available) and map the closest
    # result to a Match(source="beatport").
    raise NotImplementedError("Beatport adapter not yet implemented")
