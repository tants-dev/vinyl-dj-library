import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session, func, or_, select

from db.models import BpmKeyData, Release, Track
from db.session import get_session
from enrich.audio_analysis import analyze_sample
from enrich.camelot import to_camelot

router = APIRouter()


@router.post("/analyze-clip")
async def analyze_clip(file: UploadFile):
    """Accept an audio clip and return BPM + key via local librosa analysis."""
    ext = os.path.splitext(file.filename or "")[1] or ".bin"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        match = analyze_sample(tmp_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Audio analysis failed — check that ffmpeg is installed if using webm/mp4: {exc}",
        )
    finally:
        os.unlink(tmp_path)

    return {
        "bpm": match.bpm,
        "key": match.key,
        "camelot": to_camelot(match.key),
        "confidence": match.confidence,
    }


@router.get("/track-search")
def track_search(q: str = "", session: Session = Depends(get_session)):
    """JSON search for tracks — used by the clip analysis assign-to-track flow."""
    if not q.strip():
        return []

    pattern = f"%{q.lower()}%"
    rows = session.exec(
        select(Track, Release)
        .join(Release)
        .where(
            or_(
                func.lower(Track.title).like(pattern),
                func.lower(Track.artists).like(pattern),
                func.lower(Release.artists).like(pattern),
                func.lower(Release.title).like(pattern),
            )
        )
        .limit(10)
    ).all()

    q_lower = q.lower()

    def _rank(row):
        track, release = row
        title   = (track.title or "").lower()
        artist  = (track.artists or release.artists or "").lower()
        rel     = (release.title or "").lower()
        if q_lower in title:   return 0
        if q_lower in artist:  return 1
        return 2  # release title match

    rows = sorted(rows, key=_rank)

    return [
        {
            "id": track.id,
            "title": track.title,
            "artist": track.artists or release.artists,
            "release": release.title,
            "existing_bpm": track.bpm_key.bpm if track.bpm_key and track.bpm_key.bpm else None,
            "existing_key": track.bpm_key.camelot_key or track.bpm_key.key if track.bpm_key else None,
        }
        for track, release in rows
    ]
