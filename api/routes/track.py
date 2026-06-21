from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from db.models import BpmKeyData, Track
from db.session import get_session
from enrich.camelot import to_camelot

router = APIRouter()


class BpmKeyUpdate(BaseModel):
    bpm: Optional[float] = None
    key: Optional[str] = None


@router.patch("/track/{track_id}/bpm-key")
def update_bpm_key(
    track_id: int, update: BpmKeyUpdate, session: Session = Depends(get_session)
):
    track = session.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = session.get(BpmKeyData, track_id)
    if existing:
        existing.bpm = update.bpm
        existing.key = update.key
        existing.camelot_key = to_camelot(update.key)
        existing.source = "manual"
        session.add(existing)
    else:
        session.add(
            BpmKeyData(
                track_id=track_id,
                bpm=update.bpm,
                key=update.key,
                camelot_key=to_camelot(update.key),
                source="manual",
            )
        )
    session.commit()
    return {"track_id": track_id, "bpm": update.bpm, "key": update.key, "source": "manual"}
