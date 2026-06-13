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

def generate_id(users, role):
    prefix = "A" if role == "admin_sub" else "D"
    existing = [u for u in users if u["id"].startswith(prefix)]
    if not existing:
        return f"{prefix}1"
    max_num = max(int(u["id"][1:]) for u in existing)
    return f"{prefix}{max_num + 1}"

@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request, search: str = ""):
    users = load_users()
    filtered = [u for u in users if u.get("role") != "admin_main"]
    if search:
        filtered = [u for u in filtered if search.lower() in u.get("id", "").lower() or search in u.get("full_name", "")]
    return templates.TemplateResponse(request, "users.html", {"users": filtered, "search": search})

@router.get("/users/add/{role}", response_class=HTMLResponse)
async def user_add_page(request: Request, role: str):
    return templates.TemplateResponse(request, "user_form.html", {"user": None, "role": role, "action": f"/users/add/{role}", "error": None})

@router.post("/users/add/{role}", response_class=HTMLResponse)
async def user_add_submit(
    request: Request,
    role: str,
    full_name: str = Form(...),
    national_id: str = Form(...),
    phone: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    users = load_users()
    duplicate = next((u for u in users if u.get("national_id") == national_id and u.get("role") == role), None)
    if duplicate:
        role_label = "ادمین زیرشاخه" if role == "admin_sub" else "راننده"
        error = f"کاربری با این کد ملی قبلاً به عنوان {role_label} ثبت شده است"
        return templates.TemplateResponse(request, "user_form.html", {"user": None, "role": role, "action": f"/users/add/{role}", "error": error})
    new_user = {
        "id": generate_id(users, role),
        "full_name": full_name,
        "national_id": national_id,
        "phone": phone,
        "username": username,
        "password": password,
        "role": role,
        "status": "approved" if role == "admin_sub" else "pending"
    }
    users.append(new_user)
    save_users(users)
    return RedirectResponse(url="/users", status_code=302)

@router.get("/users/edit/{user_id}", response_class=HTMLResponse)
async def user_edit_page(request: Request, user_id: str):
    users = load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return RedirectResponse(url="/users")
    return templates.TemplateResponse(request, "user_form.html", {"user": user, "role": user["role"], "action": f"/users/edit/{user_id}", "error": None})

@router.post("/users/edit/{user_id}", response_class=HTMLResponse)
async def user_edit_submit(
    request: Request,
    user_id: str,
    full_name: str = Form(...),
    national_id: str = Form(...),
    phone: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    users = load_users()
    current_user = next((u for u in users if u["id"] == user_id), None)
    duplicate = next((u for u in users if u.get("national_id") == national_id and u.get("role") == current_user["role"] and u["id"] != user_id), None)
    if duplicate:
        role_label = "ادمین زیرشاخه" if current_user["role"] == "admin_sub" else "راننده"
        error = f"کاربری با این کد ملی قبلاً به عنوان {role_label} ثبت شده است"
        return templates.TemplateResponse(request, "user_form.html", {"user": current_user, "role": current_user["role"], "action": f"/users/edit/{user_id}", "error": error})
    for u in users:
        if u["id"] == user_id:
            u["full_name"] = full_name
            u["national_id"] = national_id
            u["phone"] = phone
            u["username"] = username
            if password:
                u["password"] = password
            break
    save_users(users)
    return RedirectResponse(url="/users", status_code=302)

@router.get("/users/delete/{user_id}", response_class=HTMLResponse)
async def user_delete(request: Request, user_id: str):
    users = load_users()
    users = [u for u in users if u["id"] != user_id]
    save_users(users)
    return RedirectResponse(url="/users", status_code=302)

@router.get("/approve-drivers", response_class=HTMLResponse)
async def approve_drivers(request: Request):
    users = load_users()
    pending = [u for u in users if u.get("role") == "driver" and u.get("status") == "pending"]
    return templates.TemplateResponse(request, "approve_drivers.html", {"drivers": pending})

@router.get("/approve-drivers/{user_id}/{action}", response_class=HTMLResponse)
async def approve_driver_action(request: Request, user_id: str, action: str):
    users = load_users()
    if action == "approve":
        for u in users:
            if u["id"] == user_id:
                u["status"] = "approved"
                break
        save_users(users)
    elif action == "reject":
        users = [u for u in users if u["id"] != user_id]
        save_users(users)
    return RedirectResponse(url="/approve-drivers", status_code=302) 