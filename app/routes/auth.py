import pymysql
from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature
from app.database import call_sp, call_sp_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

SECRET_KEY = "cargo-system-secret-key-2024"
serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_session(user_id: str, role: str):
    return serializer.dumps({"id": user_id, "role": role})

def get_session(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=86400)
        return data
    except BadSignature:
        return None

def require_admin(request: Request):
    session = get_session(request)
    if not session:
        return None
    if session["role"] not in ["admin_main", "admin_sub"]:
        return None
    return session

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    admin = call_sp_one("sp_get_admin_main")
    if not admin:
        return RedirectResponse(url="/setup")
    session = get_session(request)
    if session:
        if session["role"] == "driver":
            return RedirectResponse(url=f"/driver/{session['id']}")
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    admin = call_sp_one("sp_get_admin_main")
    if admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "setup.html")

@router.post("/setup", response_class=HTMLResponse)
async def setup_submit(request: Request, username: str = Form(...), password: str = Form(...), full_name: str = Form(...), phone: str = Form(...)):
    admin = call_sp_one("sp_get_admin_main")
    if admin:
        return RedirectResponse(url="/login")
    call_sp("sp_create_user", ("A1", full_name, None, phone, username, password, "admin_main", "approved"))
    return RedirectResponse(url="/login", status_code=302)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    session = get_session(request)
    if session:
        if session["role"] == "driver":
            return RedirectResponse(url=f"/driver/{session['id']}")
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "login.html")

@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    user = call_sp_one("sp_get_user_by_username", (username,))
    if not user or user["password"] != password:
        return templates.TemplateResponse(request, "login.html", {"error": "نام کاربری یا رمز عبور اشتباه است"})
    if user["role"] == "driver":
        if user.get("status") != "approved":
            return templates.TemplateResponse(request, "login.html", {"error": "حساب شما هنوز تایید نشده است"})
    token = create_session(user["id"], user["role"])
    if user["role"] == "driver":
        redirect = RedirectResponse(url=f"/driver/{user['id']}", status_code=302)
    else:
        redirect = RedirectResponse(url="/dashboard", status_code=302)
    redirect.set_cookie("session", token, httponly=True, max_age=86400)
    return redirect

@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    return response
