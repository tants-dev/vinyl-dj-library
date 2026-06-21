import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from db.session import get_session
from sync.discogs_sync import sync_collection

router = APIRouter()


@router.post("/sync", response_class=HTMLResponse)
def trigger_sync(session: Session = Depends(get_session)):
    try:
        count = sync_collection(session)
        return f'<p class="empty-state">Synced {count} release(s).</p>'
    except (NotImplementedError, RuntimeError) as exc:
        return f'<p class="empty-state">{exc}</p>'
    except httpx.HTTPError as exc:
        return f'<p class="empty-state">Discogs sync failed: {exc}</p>'
