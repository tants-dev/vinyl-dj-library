"""GetSongBPM.com API adapter — open fallback BPM/key source.

Requires GETSONGBPM_API_KEY (see .env.example). Not yet implemented.
"""

import os
from typing import Optional

from enrich.sources.base import Match

API_BASE = "https://api.getsong.co"


def is_configured() -> bool:
    return bool(os.environ.get("GETSONGBPM_API_KEY"))


def lookup(artist: str, title: str) -> Optional[Match]:
    if not is_configured():
        return None
    # TODO (Phase 2): GET {API_BASE}/search/?type=both&lookup=song:{title} artist:{artist}
    # and map the closest result to a Match(source="getsongbpm").
    raise NotImplementedError("GetSongBPM adapter not yet implemented")
