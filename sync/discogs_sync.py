"""Pulls the user's Discogs collection into the local SQLite DB.

Implements docs/ARCHITECTURE_TARGET.md "Discogs sync module" and
docs/ROADMAP.md Phase 1. Requires DISCOGS_TOKEN, DISCOGS_USERNAME,
DISCOGS_COLLECTION_FOLDER_ID in .env (see .env.example).

Contract confirmed against the live API:
- GET /users/{username}/collection/folders/{folder_id}/releases is
  paginated and only gives basic_information — no tracklist.
- Full tracklist requires a separate GET /releases/{release_id} call per
  release, so this does one request per release plus one per
  collection-listing page.
- Rate limit is 60 req/min authenticated (X-Discogs-Ratelimit headers
  confirm this); a fixed delay between requests keeps us safely under it
  without needing to parse those headers.
"""

import os
import time
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from sqlmodel import Session, select

from db.models import Release, Track

DISCOGS_API_BASE = "https://api.discogs.com"
USER_AGENT = "vinyl-dj-library/0.1"
REQUEST_DELAY_SECONDS = 1.1


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def _headers(token: str) -> dict:
    return {"Authorization": f"Discogs token={token}", "User-Agent": USER_AGENT}


def _join_artist_credits(artists: Optional[list]) -> Optional[str]:
    """Discogs artist arrays carry a per-artist 'join' separator (e.g. '&',
    'X', 'Feat.', ',') to glue display names together; reconstruct that
    string the same way Discogs's own 'artists_sort' field does — confirmed
    against real multi-artist releases. Disambiguator suffixes like
    "Natty (3)" are kept as-is (artists_sort keeps them too, doesn't strip
    them). The comma is the one separator that doesn't get a leading space
    (e.g. "Prozak (11), Silva Bumpa", not "Prozak (11) , Silva Bumpa").
    """
    if not artists:
        return None
    pieces = []
    for artist in artists:
        pieces.append(artist.get("name", ""))
        join = artist.get("join")
        if join == ",":
            pieces.append(", ")
        elif join:
            pieces.append(f" {join} ")
    joined = "".join(pieces).strip()
    return joined or None


def _fetch_collection_release_ids(
    username: str, folder_id: str, headers: dict
) -> List[int]:
    release_ids: List[int] = []
    page = 1
    while True:
        resp = httpx.get(
            f"{DISCOGS_API_BASE}/users/{username}/collection/folders/{folder_id}/releases",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=15,
        )
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY_SECONDS)

        data = resp.json()
        release_ids.extend(r["id"] for r in data.get("releases", []))

        pagination = data.get("pagination", {})
        if page >= pagination.get("pages", page):
            break
        page += 1

    return release_ids


def _upsert_release(session: Session, detail: dict) -> Release:
    release_id = detail["id"]
    labels = detail.get("labels") or [{}]
    formats = detail.get("formats") or [{}]
    images = detail.get("images") or []
    cover_image_url = images[0].get("uri") if images else detail.get("thumb")

    release = session.get(Release, release_id) or Release(id=release_id)
    release.title = detail.get("title", "")
    release.artists = (
        detail.get("artists_sort")
        or _join_artist_credits(detail.get("artists"))
        or "Unknown"
    )
    release.label = labels[0].get("name")
    release.catalog_number = labels[0].get("catno")
    release.year = detail.get("year") or None
    release.format = formats[0].get("name")
    release.genres = ", ".join(detail.get("genres") or []) or None
    release.styles = ", ".join(detail.get("styles") or []) or None
    release.cover_image_url = cover_image_url
    release.discogs_synced_at = datetime.now(timezone.utc).isoformat()

    session.add(release)
    return release


def _upsert_tracks(session: Session, release_id: int, tracklist: list) -> None:
    """Matches existing Track rows by (release_id, position) rather than
    replacing them wholesale, so re-syncing never orphans a previously
    synced track's BpmKeyData (manual or automated) by issuing it a new id.
    """
    for item in tracklist:
        if item.get("type_") != "track":
            continue  # skip index/heading entries (e.g. side markers)
        position = item.get("position") or ""
        existing = session.exec(
            select(Track).where(
                Track.release_id == release_id, Track.position == position
            )
        ).first()
        track = existing or Track(release_id=release_id, position=position)
        track.title = item.get("title", "")
        track.artists = _join_artist_credits(item.get("artists"))
        track.duration = item.get("duration") or None
        session.add(track)


def sync_collection(session: Session) -> int:
    """Fetch the user's Discogs collection and upsert releases/tracks into
    SQLite. Returns the number of releases synced.
    """
    token = _require_env("DISCOGS_TOKEN")
    username = _require_env("DISCOGS_USERNAME")
    folder_id = os.environ.get("DISCOGS_COLLECTION_FOLDER_ID", "0")
    headers = _headers(token)

    release_ids = _fetch_collection_release_ids(username, folder_id, headers)

    for release_id in release_ids:
        resp = httpx.get(
            f"{DISCOGS_API_BASE}/releases/{release_id}", headers=headers, timeout=15
        )
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY_SECONDS)

        detail = resp.json()
        _upsert_release(session, detail)
        _upsert_tracks(session, release_id, detail.get("tracklist") or [])

    session.commit()
    return len(release_ids)
