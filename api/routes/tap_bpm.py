from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from db.models import Track
from db.session import get_session

router = APIRouter()


@router.get("/tap-bpm", response_class=HTMLResponse)
def tap_bpm(request: Request, track_id: Optional[int] = None, session: Session = Depends(get_session)):
    preset_track = None
    if track_id:
        t = session.get(Track, track_id)
        if t:
            preset_track = {
                "id": t.id,
                "title": t.title,
                "artist": t.artists or t.release.artists,
                "cover_art": t.release.cover_image_url,
                "existing_bpm": t.bpm_key.bpm if t.bpm_key and t.bpm_key.bpm else None,
                "existing_key": (t.bpm_key.camelot_key or t.bpm_key.key) if t.bpm_key else None,
            }
    return request.app.state.templates.TemplateResponse(
        request, "tap_bpm.html", {"preset_track": preset_track}
    )
