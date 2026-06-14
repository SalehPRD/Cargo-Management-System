import json
import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CARGOS_FILE = "data/cargos.json"

def load_cargos():
    if not os.path.exists(CARGOS_FILE):
        return []
    with open(CARGOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cargos(cargos):
    with open(CARGOS_FILE, "w", encoding="utf-8") as f:
        json.dump(cargos, f, ensure_ascii=False, indent=2)

def generate_id(cargos):
    if not cargos:
        return "C1"
    max_id = max(int(c["id"][1:]) for c in cargos)
    return f"C{max_id + 1}"

@router.get("/cargos", response_class=HTMLResponse)
async def cargos_list(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargos = load_cargos()
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
    cargos = load_cargos()
    new_cargo = {
        "id": generate_id(cargos),
        "origin": origin,
        "destination": destination,
        "weight": weight,
        "product_name": product_name,
        "loader_type": loader_type,
        "status": "waiting"
    }
    cargos.append(new_cargo)
    save_cargos(cargos)
    return RedirectResponse(url="/cargos", status_code=302)

@router.get("/cargos/edit/{cargo_id}", response_class=HTMLResponse)
async def cargo_edit_page(request: Request, cargo_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargos = load_cargos()
    cargo = next((c for c in cargos if c["id"] == cargo_id), None)
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
    cargos = load_cargos()
    for c in cargos:
        if c["id"] == cargo_id:
            c["origin"] = origin
            c["destination"] = destination
            c["weight"] = weight
            c["product_name"] = product_name
            c["loader_type"] = loader_type
            break
    save_cargos(cargos)
    return RedirectResponse(url="/cargos", status_code=302)

@router.get("/cargos/delete/{cargo_id}", response_class=HTMLResponse)
async def cargo_delete(request: Request, cargo_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargos = load_cargos()
    cargos = [c for c in cargos if c["id"] != cargo_id]
    save_cargos(cargos)
    return RedirectResponse(url="/cargos", status_code=302)
