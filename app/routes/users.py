from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin
from app.database import call_sp, call_sp_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def generate_user_id(role):
    prefix = "A" if role == "admin_sub" else "D"
    result = call_sp_one("sp_get_max_id_by_prefix", (prefix,))
    max_num = result["max_num"] if result and result["max_num"] else 0
    return f"{prefix}{max_num + 1}"

@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request, search: str = ""):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    users = call_sp("sp_get_all_users")
    if search:
        users = [u for u in users if search.lower() in u.get("id", "").lower() or search in u.get("full_name", "")]
    return templates.TemplateResponse(request, "users.html", {"users": users, "search": search})

@router.get("/users/add/{role}", response_class=HTMLResponse)
async def user_add_page(request: Request, role: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
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
    if not require_admin(request):
        return RedirectResponse(url="/login")
    duplicate = call_sp_one("sp_check_national_id", (national_id, role))
    if duplicate and duplicate["cnt"] > 0:
        role_label = "ادمین زیرشاخه" if role == "admin_sub" else "راننده"
        error = f"کاربری با این کد ملی قبلاً به عنوان {role_label} ثبت شده است"
        return templates.TemplateResponse(request, "user_form.html", {"user": None, "role": role, "action": f"/users/add/{role}", "error": error})
    user_id = generate_user_id(role)
    status = "approved" if role == "admin_sub" else "pending"
    call_sp("sp_create_user", (user_id, full_name, national_id, phone, username, password, role, status))
    return RedirectResponse(url="/users", status_code=302)

@router.get("/users/edit/{user_id}", response_class=HTMLResponse)
async def user_edit_page(request: Request, user_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    user = call_sp_one("sp_get_user_by_id", (user_id,))
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
    if not require_admin(request):
        return RedirectResponse(url="/login")
    current_user = call_sp_one("sp_get_user_by_id", (user_id,))
    duplicate = call_sp_one("sp_check_national_id", (national_id, current_user["role"]))
    if duplicate and duplicate["cnt"] > 0:
        existing = call_sp_one("sp_get_user_by_id", (user_id,))
        if existing["national_id"] != national_id:
            role_label = "ادمین زیرشاخه" if current_user["role"] == "admin_sub" else "راننده"
            error = f"کاربری با این کد ملی قبلاً به عنوان {role_label} ثبت شده است"
            return templates.TemplateResponse(request, "user_form.html", {"user": current_user, "role": current_user["role"], "action": f"/users/edit/{user_id}", "error": error})
    call_sp("sp_update_user", (user_id, full_name, national_id, phone, password if password else current_user["password"]))
    return RedirectResponse(url="/users", status_code=302)

@router.get("/users/delete/{user_id}", response_class=HTMLResponse)
async def user_delete(request: Request, user_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    call_sp("sp_delete_user", (user_id,))
    return RedirectResponse(url="/users", status_code=302)

@router.get("/approve-drivers", response_class=HTMLResponse)
async def approve_drivers(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    drivers = call_sp("sp_get_pending_drivers")
    return templates.TemplateResponse(request, "approve_drivers.html", {"drivers": drivers})

@router.get("/approve-drivers/{user_id}/{action}", response_class=HTMLResponse)
async def approve_driver_action(request: Request, user_id: str, action: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    if action == "approve":
        call_sp("sp_approve_driver", (user_id,))
    elif action == "reject":
        call_sp("sp_delete_user", (user_id,))
    return RedirectResponse(url="/approve-drivers", status_code=302)
