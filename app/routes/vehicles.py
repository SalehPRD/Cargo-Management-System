import json
import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

VEHICLES_FILE = "data/vehicles.json"
USERS_FILE = "data/users.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_vehicles(vehicles):
    with open(VEHICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(vehicles, f, ensure_ascii=False, indent=2)

def validate_vehicle(vehicles, smart_number, plate, loader_type, exclude_id=None):
    for v in vehicles:
        if exclude_id and v["id"] == exclude_id:
            continue
        if v["smart_number"] == smart_number and v["plate"] != plate:
            return "این شماره هوشمند قبلاً برای پلاک دیگری ثبت شده است"
        if v["smart_number"] == smart_number and v["plate"] == plate and v["loader_type"] == loader_type:
            return "این ماشین با همین نوع بارگیر قبلاً ثبت شده است"
    return None

@router.get("/vehicles", response_class=HTMLResponse)
async def vehicles_list(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    vehicles = load_json(VEHICLES_FILE)
    users = load_json(USERS_FILE)
    drivers = {u["id"]: u["full_name"] for u in users if u.get("role") == "driver"}
    return templates.TemplateResponse(request, "vehicles.html", {"vehicles": vehicles, "drivers": drivers})

@router.get("/vehicles/add", response_class=HTMLResponse)
async def vehicle_add_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    users = load_json(USERS_FILE)
    drivers = [u for u in users if u.get("role") == "driver" and u.get("status") == "approved"]
    return templates.TemplateResponse(request, "vehicle_form.html", {"vehicle": None, "drivers": drivers, "action": "/vehicles/add", "error": None})

@router.post("/vehicles/add", response_class=HTMLResponse)
async def vehicle_add_submit(
    request: Request,
    smart_number: str = Form(...),
    plate: str = Form(...),
    loader_type: str = Form(...),
    model: str = Form(...),
    driver_id: str = Form(...)
):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    vehicles = load_json(VEHICLES_FILE)
    users = load_json(USERS_FILE)
    drivers = [u for u in users if u.get("role") == "driver" and u.get("status") == "approved"]
    error = validate_vehicle(vehicles, smart_number, plate, loader_type)
    if error:
        return templates.TemplateResponse(request, "vehicle_form.html", {"vehicle": None, "drivers": drivers, "action": "/vehicles/add", "error": error})
    new_vehicle = {
        "id": f"V{len(vehicles) + 1}",
        "smart_number": smart_number,
        "plate": plate,
        "loader_type": loader_type,
        "model": model,
        "driver_id": driver_id,
        "status": "free"
    }
    vehicles.append(new_vehicle)
    save_vehicles(vehicles)
    return RedirectResponse(url="/vehicles", status_code=302)

@router.get("/vehicles/edit/{vehicle_id}", response_class=HTMLResponse)
async def vehicle_edit_page(request: Request, vehicle_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    vehicles = load_json(VEHICLES_FILE)
    users = load_json(USERS_FILE)
    vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not vehicle:
        return RedirectResponse(url="/vehicles")
    drivers = [u for u in users if u.get("role") == "driver" and u.get("status") == "approved"]
    return templates.TemplateResponse(request, "vehicle_form.html", {"vehicle": vehicle, "drivers": drivers, "action": f"/vehicles/edit/{vehicle_id}", "error": None})

@router.post("/vehicles/edit/{vehicle_id}", response_class=HTMLResponse)
async def vehicle_edit_submit(
    request: Request,
    vehicle_id: str,
    smart_number: str = Form(...),
    plate: str = Form(...),
    loader_type: str = Form(...),
    model: str = Form(...),
    driver_id: str = Form(...)
):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    vehicles = load_json(VEHICLES_FILE)
    users = load_json(USERS_FILE)
    drivers = [u for u in users if u.get("role") == "driver" and u.get("status") == "approved"]
    error = validate_vehicle(vehicles, smart_number, plate, loader_type, exclude_id=vehicle_id)
    if error:
        vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)
        return templates.TemplateResponse(request, "vehicle_form.html", {"vehicle": vehicle, "drivers": drivers, "action": f"/vehicles/edit/{vehicle_id}", "error": error})
    for v in vehicles:
        if v["id"] == vehicle_id:
            v["smart_number"] = smart_number
            v["plate"] = plate
            v["loader_type"] = loader_type
            v["model"] = model
            v["driver_id"] = driver_id
            break
    save_vehicles(vehicles)
    return RedirectResponse(url="/vehicles", status_code=302)

@router.get("/vehicles/delete/{vehicle_id}", response_class=HTMLResponse)
async def vehicle_delete(request: Request, vehicle_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    vehicles = load_json(VEHICLES_FILE)
    vehicles = [v for v in vehicles if v["id"] != vehicle_id]
    save_vehicles(vehicles)
    return RedirectResponse(url="/vehicles", status_code=302)
