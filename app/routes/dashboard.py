from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin, get_session
from app.database import call_sp, call_sp_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session = require_admin(request)
    if not session:
        return RedirectResponse(url="/login")
    current_user = call_sp_one("sp_get_user_by_id", (session["id"],))
    cargos = call_sp("sp_get_all_cargos")
    users = call_sp("sp_get_all_users")
    stats = {
        "total_cargos": len(cargos),
        "waiting": sum(1 for c in cargos if c["status"] == "waiting"),
        "loaded": sum(1 for c in cargos if c["status"] == "loaded"),
        "in_progress": sum(1 for c in cargos if c["status"] == "selected"),
        "total_drivers": sum(1 for u in users if u["role"] == "driver"),
    }
    return templates.TemplateResponse(request, "dashboard.html", {"stats": stats, "current_user": current_user})
