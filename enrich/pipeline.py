"""Enrichment pipeline: fills in BPM/key for tracks with none yet.

Tries sources in priority order per docs/DECISIONS.md ADR-003:
Beatport -> GetSongBPM -> (manual local audio analysis is user-triggered,
see enrich/audio_analysis.py, not run automatically by this pipeline).
Never overwrites a track whose existing BpmKeyData.source == "manual".
"""

from typing import List

from sqlmodel import Session, select

from db.models import BpmKeyData, Track
from enrich.camelot import to_camelot
from enrich.sources import beatport, getsongbpm
from enrich.sources.base import Match

SOURCES_IN_PRIORITY_ORDER = [beatport, getsongbpm]


def _find_match(artist: str, title: str) -> "Match | None":
    for source in SOURCES_IN_PRIORITY_ORDER:
        if not source.is_configured():
            continue
        match = source.lookup(artist, title)
        if match:
            return match
    return None


def enrich_unmatched_tracks(session: Session) -> int:
    """Run the pipeline over every track with no BPM/key row (or none from
    manual entry). Returns the number of tracks newly enriched.
    """
    tracks: List[Track] = session.exec(
        select(Track).where(~Track.bpm_key.has())
    ).all()

    enriched = 0
    for track in tracks:
        match = _find_match(track.artists or "", track.title)
        if not match:
            continue
        session.add(
            BpmKeyData(
                track_id=track.id,
                bpm=match.bpm,
                key=match.key,
                camelot_key=to_camelot(match.key),
                source=match.source,
                confidence=match.confidence,
            )
        )
        enriched += 1

    session.commit()
    return enriched
