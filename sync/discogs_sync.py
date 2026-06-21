"""Pulls the user's Discogs collection into the local SQLite DB.

Implements docs/ARCHITECTURE_TARGET.md "Discogs sync module" and
docs/ROADMAP.md Phase 1. Not yet implemented — requires DISCOGS_TOKEN,
DISCOGS_USERNAME, DISCOGS_COLLECTION_FOLDER_ID in .env (see .env.example).
"""

import os

DISCOGS_API_BASE = "https://api.discogs.com"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def sync_collection() -> int:
    """Fetch the user's Discogs collection and upsert releases/tracks into SQLite.

    Returns the number of releases synced.
    """
    token = _require_env("DISCOGS_TOKEN")
    username = _require_env("DISCOGS_USERNAME")
    folder_id = os.environ.get("DISCOGS_COLLECTION_FOLDER_ID", "0")

    headers = {
        "Authorization": f"Discogs token={token}",
        "User-Agent": "vinyl-dj-library/0.1",
    }
    url = f"{DISCOGS_API_BASE}/users/{username}/collection/folders/{folder_id}/releases"

    # TODO (Phase 1): paginate through results, fetch full release detail
    # per item (tracklist, label, catalog number, cover art), upsert into
    # Release/Track tables via db.session, and respect the 60 req/min rate
    # limit (see docs/DECISIONS.md ADR-005).
    raise NotImplementedError(
        "Discogs sync not yet implemented — see docs/ROADMAP.md Phase 1. "
        f"Would have called: GET {url}"
    )
