from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin, get_session
from app.database import call_sp, call_sp_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/change-admin", response_class=HTMLResponse)
async def change_admin_page(request: Request):
    session = get_session(request)
    if not session or session["role"] != "admin_main":
        return RedirectResponse(url="/login")
    current_admin = call_sp_one("sp_get_admin_main")
    return templates.TemplateResponse(request, "change_admin.html", {"current_admin": current_admin, "error": None})

@router.post("/change-admin", response_class=HTMLResponse)
async def change_admin_submit(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    session = get_session(request)
    if not session or session["role"] != "admin_main":
        return RedirectResponse(url="/login")
    current_admin = call_sp_one("sp_get_admin_main")
    if current_admin:
        call_sp("sp_create_admin_history", (current_admin["full_name"], current_admin["username"], current_admin["phone"]))
        call_sp("sp_delete_user", (current_admin["id"],))
    call_sp("sp_create_user", ("A1", full_name, None, phone, username, password, "admin_main", "approved"))
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    return response

@router.get("/admin-history", response_class=HTMLResponse)
async def admin_history_page(request: Request):
    session = get_session(request)
    if not session or session["role"] != "admin_main":
        return RedirectResponse(url="/login")
    history = call_sp("sp_get_admin_history")
    return templates.TemplateResponse(request, "admin_history.html", {"history": history})
