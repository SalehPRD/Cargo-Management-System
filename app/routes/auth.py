import json
import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

USERS_FILE = "data/users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    users = load_users()
    admins = [u for u in users if u["role"] == "admin_main"]
    if not admins:
        return RedirectResponse(url="/setup")
    return RedirectResponse(url="/login")

@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    users = load_users()
    admins = [u for u in users if u["role"] == "admin_main"]
    if admins:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "setup.html")

@router.post("/setup", response_class=HTMLResponse)
async def setup_submit(request: Request, username: str = Form(...), password: str = Form(...), full_name: str = Form(...), phone: str = Form(...)):
    users = load_users()
    admins = [u for u in users if u["role"] == "admin_main"]
    if admins:
        return RedirectResponse(url="/login")
    new_admin = {
        "id": "A1",
        "username": username,
        "password": password,
        "full_name": full_name,
        "phone": phone,
        "role": "admin_main"
    }
    users.append(new_admin)
    save_users(users)
    return RedirectResponse(url="/login", status_code=302)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    users = load_users()
    user = next((u for u in users if u["username"] == username and u["password"] == password), None)
    if not user:
        return templates.TemplateResponse(request, "login.html", {"error": "نام کاربری یا رمز عبور اشتباه است"})
    return RedirectResponse(url="/dashboard", status_code=302)