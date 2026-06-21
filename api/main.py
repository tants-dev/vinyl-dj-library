from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from db.models import Release, Track
from db.session import get_session, init_db
from api.routes import enrich, release, search, sync, system, tap_bpm, track
from api.routes.search import browse_releases, get_filter_options

load_dotenv()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Vinyl DJ Library", lifespan=lifespan)
app.state.templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

app.include_router(search.router)
app.include_router(release.router)
app.include_router(sync.router)
app.include_router(enrich.router)
app.include_router(track.router)
app.include_router(system.router)
app.include_router(tap_bpm.router)


def _format_last_synced(session: Session) -> str:
    raw = session.exec(select(func.max(Release.discogs_synced_at))).one()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return raw


@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    unenriched_count = session.exec(
        select(func.count())
        .select_from(Track)
        .where(~Track.bpm_key.has())
    ).one()

    return app.state.templates.TemplateResponse(
        request,
        "index.html",
        {
            "last_synced": _format_last_synced(session),
            "unenriched_count": unenriched_count,
            "releases": browse_releases(session),
            "filter_options": get_filter_options(session),
        },
    )
