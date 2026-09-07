from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin
from app.database import call_sp, call_sp_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def generate_cargo_id():
    result = call_sp_one("sp_get_max_cargo_id")
    max_num = result["max_num"] if result and result["max_num"] else 0
    return f"C{max_num + 1}"

@router.get("/cargos", response_class=HTMLResponse)
async def cargos_list(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargos = call_sp("sp_get_all_cargos")
    return templates.TemplateResponse(request, "cargos.html", {"cargos": cargos})

@router.get("/cargos/add", response_class=HTMLResponse)
async def cargo_add_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "cargo_form.html", {"cargo": None, "action": "/cargos/add"})

@router.post("/cargos/add", response_class=HTMLResponse)
async def cargo_add_submit(
    request: Request,
    origin: str = Form(...),
    destination: str = Form(...),
    weight: str = Form(...),
    product_name: str = Form(...),
    loader_type: str = Form(...)
):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargo_id = generate_cargo_id()
    call_sp("sp_create_cargo", (cargo_id, product_name, origin, destination, weight, loader_type))
    return RedirectResponse(url="/cargos", status_code=302)

@router.get("/cargos/edit/{cargo_id}", response_class=HTMLResponse)
async def cargo_edit_page(request: Request, cargo_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargo = call_sp_one("sp_get_cargo_by_id", (cargo_id,))
    if not cargo:
        return RedirectResponse(url="/cargos")
    return templates.TemplateResponse(request, "cargo_form.html", {"cargo": cargo, "action": f"/cargos/edit/{cargo_id}"})

@router.post("/cargos/edit/{cargo_id}", response_class=HTMLResponse)
async def cargo_edit_submit(
    request: Request,
    cargo_id: str,
    origin: str = Form(...),
    destination: str = Form(...),
    weight: str = Form(...),
    product_name: str = Form(...),
    loader_type: str = Form(...)
):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    call_sp("sp_update_cargo", (cargo_id, product_name, origin, destination, weight, loader_type))
    return RedirectResponse(url="/cargos", status_code=302)

@router.get("/cargos/delete/{cargo_id}", response_class=HTMLResponse)
async def cargo_delete(request: Request, cargo_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    call_sp("sp_delete_cargo", (cargo_id,))
    return RedirectResponse(url="/cargos", status_code=302)