from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from db.models import Track
from db.session import get_session, init_db
from api.routes import enrich, release, search, sync, track

load_dotenv()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Vinyl DJ Library")
app.state.templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

app.include_router(search.router)
app.include_router(release.router)
app.include_router(sync.router)
app.include_router(enrich.router)
app.include_router(track.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    unenriched_count = session.exec(
        select(func.count())
        .select_from(Track)
        .where(~Track.bpm_key.has())
    ).one()

    return app.state.templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "last_synced": None,
            "unenriched_count": unenriched_count,
        },
    )
