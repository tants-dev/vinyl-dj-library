from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from db.models import Release, Track
from db.session import get_session

router = APIRouter()


@router.get("/release/{release_id}", response_class=HTMLResponse)
def release_detail(
    release_id: int, request: Request, session: Session = Depends(get_session)
):
    release = session.get(Release, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    tracks = session.exec(
        select(Track).where(Track.release_id == release_id).order_by(Track.position)
    ).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "release.html",
        {"release": release, "tracks": tracks, "featured_track": None},
    )
