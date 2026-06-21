"""Shared types for BPM/key source adapters.

Each adapter in enrich/sources/ implements `lookup(artist, title) -> Match | None`
so enrich/pipeline.py can try them in priority order (see docs/DECISIONS.md ADR-003).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Match:
    bpm: Optional[float]
    key: Optional[str]
    source: str
    confidence: Optional[float] = None
