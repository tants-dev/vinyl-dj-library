"""Enrichment pipeline: fills in BPM/key for tracks with none yet.

Tries sources in priority order per docs/DECISIONS.md ADR-003:
Beatport -> GetSongBPM -> (manual local audio analysis is user-triggered,
see enrich/audio_analysis.py, not run automatically by this pipeline).
Never overwrites a track whose existing BpmKeyData.source == "manual".
"""

import logging
from typing import List

import httpx
from sqlmodel import Session, select

from db.models import BpmKeyData, Track
from enrich.camelot import to_camelot
from enrich.sources import beatport, getsongbpm
from enrich.sources.base import Match

logger = logging.getLogger(__name__)

SOURCES_IN_PRIORITY_ORDER = [beatport, getsongbpm]


def _find_match(artist: str, title: str) -> "Match | None":
    for source in SOURCES_IN_PRIORITY_ORDER:
        if not source.is_configured():
            continue
        try:
            match = source.lookup(artist, title)
        except httpx.HTTPError:
            # A network blip or bad response from one source shouldn't abort
            # enrichment for every other track in the batch — log and move
            # on to the next source / track.
            logger.warning(
                "BPM/key lookup failed via %s for %r", source.__name__, title,
                exc_info=True,
            )
            continue
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
        # Most vinyl isn't a various-artists compilation, so Track.artists
        # is None and the real credit lives on the release (same fallback
        # api/routes/search.py already uses for display).
        artist = track.artists or (track.release.artists if track.release else "")
        match = _find_match(artist or "", track.title)
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
