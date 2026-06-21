"""GetSongBPM.com API adapter — open, self-serve fallback BPM/key source
(no partner approval gate, unlike Beatport — see docs/DECISIONS.md ADR-003).

Requires GETSONGBPM_API_KEY (see .env.example). API docs: https://getsongbpm.com/api

The API's /search/ endpoint does NOT filter by artist server-side — an
"artist" query param is silently ignored, and the documented-looking
"song:{title} artist:{artist}" combined lookup syntax just searches for
that literal string as a title and matches nothing. Confirmed by hitting
the live endpoint directly. The only thing that actually works is a
title-only search (type=song, lookup={title}), which returns up to ~30
results across every artist with a matching title — so this adapter
searches by title and picks the first result whose artist name matches.
If the right artist isn't within that result window, there's no match;
that's a real coverage limit of the free API, not a bug here.
"""

import os
from typing import List, Optional

import httpx

from enrich.sources.base import Match

API_BASE = "https://api.getsong.co"

# A bare httpx.get() per call opens a fresh TCP+TLS connection every time --
# measured at ~173ms/request vs ~68ms/request reusing one persistent Client
# (2.5x faster) against the real API. enrich_unmatched_tracks() calls
# lookup() once per unmatched track (in the hundreds for a real collection),
# so this client is shared across that whole run rather than recreated each
# call. Created lazily so tests never touch the network unless they choose
# to.
_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=10)
    return _client

# GetSongBPM's "key_of" field doesn't always use the same enharmonic spelling
# enrich/camelot.py's table expects (e.g. it may return "C#" where the
# Camelot table wants "Db" for major, but "C#" for minor). This maps
# (pitch class as returned, mode) -> the canonical note name camelot.py uses,
# so every value here round-trips through to_camelot() to a real code.
_NOTE_SPELLING = {
    ("C", "major"): "C", ("C", "minor"): "C",
    ("C#", "major"): "Db", ("Db", "major"): "Db",
    ("C#", "minor"): "C#", ("Db", "minor"): "C#",
    ("D", "major"): "D", ("D", "minor"): "D",
    ("D#", "major"): "Eb", ("Eb", "major"): "Eb",
    ("D#", "minor"): "D#", ("Eb", "minor"): "D#",
    ("E", "major"): "E", ("E", "minor"): "E",
    ("F", "major"): "F", ("F", "minor"): "F",
    ("F#", "major"): "F#", ("Gb", "major"): "F#",
    ("F#", "minor"): "F#", ("Gb", "minor"): "F#",
    ("G", "major"): "G", ("G", "minor"): "G",
    ("G#", "major"): "Ab", ("Ab", "major"): "Ab",
    ("G#", "minor"): "G#", ("Ab", "minor"): "G#",
    ("A", "major"): "A", ("A", "minor"): "A",
    ("A#", "major"): "Bb", ("Bb", "major"): "Bb",
    ("A#", "minor"): "Bb", ("Bb", "minor"): "Bb",
    ("B", "major"): "B", ("B", "minor"): "B",
}


def _parse_key_of(key_of: Optional[str]) -> Optional[str]:
    """'C#m' -> 'C# minor', 'Bb' -> 'Bb major', 'Gb' -> 'F# major'. None if
    missing or not a note we recognize. The live API returns the unicode
    sharp sign '♯' (U+266F) rather than ASCII '#' (e.g. 'G♯m'), confirmed
    against real responses — normalized here before parsing.
    """
    if not key_of:
        return None
    raw = key_of.strip().replace("♯", "#").replace("♭", "b")
    if not raw:
        return None

    if raw.endswith("m") and len(raw) > 1:
        mode, note = "minor", raw[:-1]
    else:
        mode, note = "major", raw

    canonical_note = _NOTE_SPELLING.get((note, mode))
    if not canonical_note:
        return None
    return f"{canonical_note} {mode}"


def _normalize_artist(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _artist_matches(wanted: str, candidate: str) -> bool:
    # Exact match only (after case/whitespace normalization) rather than
    # substring containment — substring matching produces real false
    # positives (e.g. "Air" matching "Fairground Attraction"), which would
    # silently attribute the wrong track's BPM/key. A missed match falls
    # through to the next source or manual entry; a wrong match doesn't.
    wanted = _normalize_artist(wanted)
    candidate = _normalize_artist(candidate)
    return bool(wanted) and wanted == candidate


def is_configured() -> bool:
    return bool(os.environ.get("GETSONGBPM_API_KEY"))


def lookup(artist: str, title: str) -> Optional[Match]:
    api_key = os.environ.get("GETSONGBPM_API_KEY")
    if not api_key:
        return None

    response = _get_client().get(
        f"{API_BASE}/search/",
        params={"api_key": api_key, "type": "song", "lookup": title},
    )
    response.raise_for_status()

    results = response.json().get("search")
    if not isinstance(results, list) or not results:
        # No match looks like {"search": {"error": "no result"}} (a dict,
        # not a list) — confirmed against the live API. Guard against
        # indexing that instead of assuming a list is always returned.
        return None

    song = _find_artist_match(results, artist)
    if song is None:
        return None

    tempo = song.get("tempo")
    bpm = float(tempo) if tempo not in (None, "") else None
    key = _parse_key_of(song.get("key_of"))

    if bpm is None and key is None:
        return None

    return Match(bpm=bpm, key=key, source="getsongbpm")


def _find_artist_match(results: List[dict], artist: str) -> Optional[dict]:
    for song in results:
        candidate = (song.get("artist") or {}).get("name") or ""
        if _artist_matches(artist, candidate):
            return song
    return None
