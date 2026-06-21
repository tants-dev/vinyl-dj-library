from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from db.models import BpmKeyData, Release, Track
from db.session import get_session

router = APIRouter()


@router.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = "", session: Session = Depends(get_session)):
    results = []
    if q.strip():
        like = f"%{q.strip()}%"
        rows = session.exec(
            select(Track, Release, BpmKeyData)
            .join(Release, Track.release_id == Release.id)
            .join(BpmKeyData, BpmKeyData.track_id == Track.id, isouter=True)
            .where(
                Track.title.ilike(like)
                | Track.artists.ilike(like)
                | Release.title.ilike(like)
                | Release.artists.ilike(like)
                | Release.label.ilike(like)
                | Release.catalog_number.ilike(like)
            )
            .limit(50)
        ).all()
        for track, release, bpm_key in rows:
            results.append(
                {
                    "release_id": release.id,
                    "release_title": release.title,
                    "artists": track.artists or release.artists,
                    "position": track.position,
                    "title": track.title,
                    "cover_image_url": release.cover_image_url,
                    "bpm": bpm_key.bpm if bpm_key else None,
                    "key": bpm_key.key if bpm_key else None,
                    "camelot_key": bpm_key.camelot_key if bpm_key else None,
                }
            )

    return request.app.state.templates.TemplateResponse(
        request,
        "partials/results.html",
        {"results": results, "query": q},
    )
