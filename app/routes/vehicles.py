from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin
from app.database import call_sp, call_sp_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def generate_vehicle_id():
    result = call_sp_one("sp_get_max_vehicle_id")
    max_num = result["max_num"] if result and result["max_num"] else 0
    return f"V{max_num + 1}"

def validate_vehicle(smart_number, plate, loader_type, exclude_id=None):
    vehicles = call_sp("sp_get_all_vehicles")
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
    vehicles = call_sp("sp_get_all_vehicles")
    users = call_sp("sp_get_all_users")
    drivers = {u["id"]: u["full_name"] for u in users if u.get("role") == "driver"}
    return templates.TemplateResponse(request, "vehicles.html", {"vehicles": vehicles, "drivers": drivers})

@router.get("/vehicles/add", response_class=HTMLResponse)
async def vehicle_add_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    users = call_sp("sp_get_all_users")
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
    users = call_sp("sp_get_all_users")
    drivers = [u for u in users if u.get("role") == "driver" and u.get("status") == "approved"]
    error = validate_vehicle(smart_number, plate, loader_type)
    if error:
        return templates.TemplateResponse(request, "vehicle_form.html", {"vehicle": None, "drivers": drivers, "action": "/vehicles/add", "error": error})
    vehicle_id = generate_vehicle_id()
    call_sp("sp_create_vehicle", (vehicle_id, smart_number, plate, loader_type, model, driver_id))
    return RedirectResponse(url="/vehicles", status_code=302)

@router.get("/vehicles/edit/{vehicle_id}", response_class=HTMLResponse)
async def vehicle_edit_page(request: Request, vehicle_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    vehicle = call_sp_one("sp_get_vehicle_by_id", (vehicle_id,))
    if not vehicle:
        return RedirectResponse(url="/vehicles")
    users = call_sp("sp_get_all_users")
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
    users = call_sp("sp_get_all_users")
    drivers = [u for u in users if u.get("role") == "driver" and u.get("status") == "approved"]
    error = validate_vehicle(smart_number, plate, loader_type, exclude_id=vehicle_id)
    if error:
        vehicle = call_sp_one("sp_get_vehicle_by_id", (vehicle_id,))
        return templates.TemplateResponse(request, "vehicle_form.html", {"vehicle": vehicle, "drivers": drivers, "action": f"/vehicles/edit/{vehicle_id}", "error": error})
    call_sp("sp_update_vehicle", (vehicle_id, smart_number, plate, loader_type, model, driver_id))
    return RedirectResponse(url="/vehicles", status_code=302)

@router.get("/vehicles/delete/{vehicle_id}", response_class=HTMLResponse)
async def vehicle_delete(request: Request, vehicle_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    call_sp("sp_delete_vehicle", (vehicle_id,))
    return RedirectResponse(url="/vehicles", status_code=302)
