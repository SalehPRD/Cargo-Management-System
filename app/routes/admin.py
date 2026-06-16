import json
import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin, get_session

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

USERS_FILE = "data/users.json"
ADMIN_HISTORY_FILE = "data/admin_history.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@router.get("/change-admin", response_class=HTMLResponse)
async def change_admin_page(request: Request):
    session = get_session(request)
    if not session or session["role"] != "admin_main":
        return RedirectResponse(url="/login")
    users = load_json(USERS_FILE)
    current_admin = next((u for u in users if u.get("role") == "admin_main"), None)
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
    users = load_json(USERS_FILE)
    history = load_json(ADMIN_HISTORY_FILE)
    current_admin = next((u for u in users if u.get("role") == "admin_main"), None)
    if current_admin:
        history.append({
            "full_name": current_admin.get("full_name"),
            "username": current_admin.get("username"),
            "phone": current_admin.get("phone"),
        })
        save_json(ADMIN_HISTORY_FILE, history)
        users = [u for u in users if u.get("role") != "admin_main"]
    new_admin = {
        "id": "A1",
        "full_name": full_name,
        "phone": phone,
        "username": username,
        "password": password,
        "role": "admin_main"
    }
    users.append(new_admin)
    save_json(USERS_FILE, users)
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    return response
@router.get("/admin-history", response_class=HTMLResponse)
async def admin_history_page(request: Request):
    session = get_session(request)
    if not session or session["role"] != "admin_main":
        return RedirectResponse(url="/login")
    history = load_json(ADMIN_HISTORY_FILE)
    return templates.TemplateResponse(request, "admin_history.html", {"history": history})