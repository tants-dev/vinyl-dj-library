"""Standalone Deezer BPM probe — run once to assess coverage before building
a real adapter.

Usage:
    python probe_deezer.py          # samples 40 unmatched tracks
    python probe_deezer.py --all    # tries all unmatched tracks (slower)

Deezer's public search API requires no key. Each track object includes a
`bpm` field (float; 0 means "not on file"). This script reports:
  - match rate (Deezer returned a result with the right artist)
  - BPM fill rate (of those matches, how many had a non-zero BPM)
  - a sample of results so you can spot-check accuracy
"""

import sys
import time
from typing import Optional

import httpx
from sqlmodel import Session, select

from db.models import BpmKeyData, Release, Track
from db.session import engine

API_BASE = "https://api.deezer.com"
SAMPLE_SIZE = 40
DELAY = 0.15  # seconds between requests — Deezer allows 50 req/5s


def _normalize(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _artist_matches(wanted: str, candidate: str) -> bool:
    return bool(wanted) and _normalize(wanted) == _normalize(candidate)


def _deezer_lookup(client: httpx.Client, artist: str, title: str) -> Optional[dict]:
    """Return the first Deezer track whose artist matches, or None."""
    resp = client.get(
        f"{API_BASE}/search",
        params={"q": f'artist:"{artist}" track:"{title}"'},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json().get("data") or []
    for track in data:
        candidate = (track.get("artist") or {}).get("name") or ""
        if _artist_matches(artist, candidate):
            return track
    # Fallback: if strict artist+title search returns nothing, try title only
    # and match artist client-side (same pattern as getsongbpm adapter)
    if not data:
        resp2 = client.get(
            f"{API_BASE}/search",
            params={"q": f'track:"{title}"'},
            timeout=10,
        )
        resp2.raise_for_status()
        data2 = resp2.json().get("data") or []
        for track in data2:
            candidate = (track.get("artist") or {}).get("name") or ""
            if _artist_matches(artist, candidate):
                return track
    return None


def main() -> None:
    use_all = "--all" in sys.argv

    with Session(engine) as session:
        stmt = (
            select(Track, Release)
            .join(Release)
            .outerjoin(BpmKeyData, BpmKeyData.track_id == Track.id)
            .where(BpmKeyData.track_id == None)  # noqa: E711
        )
        rows = session.exec(stmt).all()

    if not rows:
        print("No unmatched tracks — nothing to probe.")
        return

    sample = rows if use_all else rows[:SAMPLE_SIZE]
    print(
        f"Probing {len(sample)} of {len(rows)} unmatched tracks against Deezer...\n"
    )

    matched = 0
    bpm_filled = 0
    results = []

    with httpx.Client() as client:
        for i, (track, release) in enumerate(sample, 1):
            artist = track.artists or release.artists
            title = track.title

            try:
                hit = _deezer_lookup(client, artist, title)
            except httpx.HTTPError as e:
                print(f"  [{i}/{len(sample)}] HTTP error: {e}")
                time.sleep(DELAY)
                continue

            bpm = hit.get("bpm") if hit else None
            has_bpm = bpm not in (None, 0)

            if hit:
                matched += 1
            if has_bpm:
                bpm_filled += 1

            status = "MATCH+BPM" if has_bpm else ("MATCH-no-BPM" if hit else "miss")
            print(f"  [{i:>2}/{len(sample)}] {status:<14}  {artist} — {title}"
                  + (f"  →  {bpm} BPM" if has_bpm else ""))

            results.append(
                {
                    "artist": artist,
                    "title": title,
                    "matched": bool(hit),
                    "bpm": bpm if has_bpm else None,
                    "deezer_key": hit.get("key") if hit else None,
                }
            )

            time.sleep(DELAY)

    print(f"""
--- Results ---
Tracks probed:  {len(sample)}
Artist matched: {matched}  ({matched/len(sample)*100:.0f}%)
BPM on file:    {bpm_filled}  ({bpm_filled/len(sample)*100:.0f}% of probed,
                {bpm_filled/matched*100:.0f}% of matches)
""" if matched else f"""
--- Results ---
Tracks probed:  {len(sample)}
Artist matched: 0  (0%)
BPM on file:    0
""")

    if bpm_filled:
        print("Sample of BPM results (spot-check these against known values):")
        shown = 0
        for r in results:
            if r["bpm"]:
                print(f"  {r['artist']} — {r['title']}: {r['bpm']} BPM")
                shown += 1
                if shown >= 10:
                    break


if __name__ == "__main__":
    main()
