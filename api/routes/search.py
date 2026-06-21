from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from db.models import BpmKeyData, Release, Track
from db.session import get_session

router = APIRouter()


def browse_releases(
    session: Session,
    year: Optional[int] = None,
    genre: Optional[str] = None,
    artist: Optional[str] = None,
) -> List[Release]:
    """The default/filtered list of releases shown when there's no search
    query — clicking a row goes to the full release page.
    """
    query = select(Release)
    if year:
        query = query.where(Release.year == year)
    if artist:
        query = query.where(Release.artists == artist)
    if genre:
        # genres is a comma-joined string (e.g. "Electronic, House"); LIKE is
        # case-insensitive for ASCII on SQLite, which covers genre names fine.
        query = query.where(Release.genres.contains(genre))
    return session.exec(query.order_by(Release.artists, Release.title)).all()


def get_filter_options(session: Session) -> dict:
    """Distinct years/genres/artists actually present in the collection, for
    populating the browse-list filter dropdowns.
    """
    releases = session.exec(select(Release)).all()
    years = sorted({r.year for r in releases if r.year}, reverse=True)
    artists = sorted({r.artists for r in releases if r.artists})
    genre_set = set()
    for r in releases:
        if r.genres:
            for g in r.genres.split(","):
                g = g.strip()
                if g:
                    genre_set.add(g)
    return {"years": years, "genres": sorted(genre_set), "artists": artists}


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    q: str = "",
    year: str = "",
    genre: str = "",
    artist: str = "",
    session: Session = Depends(get_session),
):
    if not q.strip():
        # year arrives as a query string ("" for an unselected <select>), not
        # an int — FastAPI's Optional[int] rejects "" with a 422 rather than
        # treating it as absent, so it's parsed manually here instead.
        year_int = int(year) if year.strip().isdigit() else None
        releases = browse_releases(
            session, year=year_int, genre=genre or None, artist=artist or None
        )
        return request.app.state.templates.TemplateResponse(
            request, "partials/release_list.html", {"releases": releases}
        )

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

    results = [
        {
            "track_id": track.id,
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
        for track, release, bpm_key in rows
    ]

    return request.app.state.templates.TemplateResponse(
        request,
        "partials/results.html",
        {"results": results, "query": q},
    )
