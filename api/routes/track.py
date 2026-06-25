from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session

from db.models import BpmKeyData, Track
from db.session import get_session
from enrich.camelot import to_camelot

router = APIRouter()


class BpmKeyUpdate(BaseModel):
    bpm: Optional[float] = None
    key: Optional[str] = None
    source: str = "manual"


@router.get("/track/{track_id}", response_class=HTMLResponse)
def track_detail(track_id: int, request: Request, session: Session = Depends(get_session)):
    track = session.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    release = track.release
    tracks = sorted(release.tracks, key=lambda t: t.position)

    return request.app.state.templates.TemplateResponse(
        request,
        "release.html",
        {"release": release, "tracks": tracks, "featured_track": track},
    )


@router.patch("/track/{track_id}/bpm-key")
def update_bpm_key(
    track_id: int,
    update: BpmKeyUpdate,
    request: Request,
    session: Session = Depends(get_session),
):
    track = session.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = session.get(BpmKeyData, track_id)
    if existing:
        existing.bpm = update.bpm
        existing.key = update.key
        existing.camelot_key = to_camelot(update.key)
        existing.source = update.source
        session.add(existing)
    else:
        session.add(
            BpmKeyData(
                track_id=track_id,
                bpm=update.bpm,
                key=update.key,
                camelot_key=to_camelot(update.key),
                source=update.source,
            )
        )
    session.commit()

    if request.headers.get("hx-request"):
        session.refresh(track)
        return request.app.state.templates.TemplateResponse(
            request, "partials/bpm_key_cell.html", {"track": track}
        )

    return {"track_id": track_id, "bpm": update.bpm, "key": update.key, "source": update.source}
