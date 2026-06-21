from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from db.session import get_session
from enrich.pipeline import SOURCES_IN_PRIORITY_ORDER, enrich_unmatched_tracks

router = APIRouter()


@router.post("/enrich", response_class=HTMLResponse)
def trigger_enrich(session: Session = Depends(get_session)):
    count = enrich_unmatched_tracks(session)
    if any(source.is_configured() for source in SOURCES_IN_PRIORITY_ORDER):
        return f'<p class="empty-state">Enriched {count} track(s).</p>'
    return (
        f'<p class="empty-state">Enriched {count} track(s). '
        "No BPM/key sources are configured yet — see .env.example.</p>"
    )
