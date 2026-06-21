"""Standard key notation -> Camelot wheel notation, for harmonic mixing.

See docs/ARCHITECTURE_TARGET.md "Data model" — camelot_key is derived and
stored alongside the standard key so search results don't need a lookup join.
"""

from typing import Optional

# Camelot wheel: maps "<root> <major|minor>" -> Camelot code.
_CAMELOT_MAP = {
    "B major": "1B", "G# minor": "1A",
    "F# major": "2B", "D# minor": "2A",
    "Db major": "3B", "Bb minor": "3A",
    "Ab major": "4B", "F minor": "4A",
    "Eb major": "5B", "C minor": "5A",
    "Bb major": "6B", "G minor": "6A",
    "F major": "7B", "D minor": "7A",
    "C major": "8B", "A minor": "8A",
    "G major": "9B", "E minor": "9A",
    "D major": "10B", "B minor": "10A",
    "A major": "11B", "F# minor": "11A",
    "E major": "12B", "C# minor": "12A",
}


def to_camelot(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    return _CAMELOT_MAP.get(key.strip())
