from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/tap-bpm", response_class=HTMLResponse)
def tap_bpm(request: Request):
    return request.app.state.templates.TemplateResponse(request, "tap_bpm.html", {})
