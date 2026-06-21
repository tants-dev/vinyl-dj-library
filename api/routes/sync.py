from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from sync.discogs_sync import sync_collection

router = APIRouter()


@router.post("/sync", response_class=HTMLResponse)
def trigger_sync():
    try:
        count = sync_collection()
        return f'<p class="empty-state">Synced {count} releases.</p>'
    except NotImplementedError as exc:
        return f'<p class="empty-state">{exc}</p>'
    except RuntimeError as exc:
        return f'<p class="empty-state">{exc}</p>'
