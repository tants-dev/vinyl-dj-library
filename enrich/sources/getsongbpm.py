"""GetSongBPM.com API adapter — open, self-serve fallback BPM/key source
(no partner approval gate, unlike Beatport — see docs/DECISIONS.md ADR-003).

Requires GETSONGBPM_API_KEY (see .env.example). API docs: https://getsongbpm.com/api
"""

import os
from typing import Optional

import httpx

from enrich.sources.base import Match

API_BASE = "https://api.getsong.co"

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
    missing or not a note we recognize.
    """
    if not key_of:
        return None
    raw = key_of.strip()
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


def is_configured() -> bool:
    return bool(os.environ.get("GETSONGBPM_API_KEY"))


def lookup(artist: str, title: str) -> Optional[Match]:
    api_key = os.environ.get("GETSONGBPM_API_KEY")
    if not api_key:
        return None

    response = httpx.get(
        f"{API_BASE}/search/",
        params={
            "api_key": api_key,
            "type": "song",
            "lookup": f"song:{title} artist:{artist}",
        },
        timeout=10,
    )
    response.raise_for_status()

    results = response.json().get("search")
    if not isinstance(results, list) or not results:
        # The API returns {"search": "No Results"} (a string) when nothing
        # matches, rather than an empty list — guard against indexing that.
        return None

    song = results[0]
    tempo = song.get("tempo")
    bpm = float(tempo) if tempo not in (None, "") else None
    key = _parse_key_of(song.get("key_of"))

    if bpm is None and key is None:
        return None

    return Match(bpm=bpm, key=key, source="getsongbpm")
