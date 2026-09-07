from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import get_session
from app.database import call_sp, call_sp_one
from app.routes.wallet import has_enough_balance, deduct_balance, QUEUE_COST

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_driver(driver_id):
    return call_sp_one("sp_get_user_by_id", (driver_id,))

def generate_queue_id():
    result = call_sp_one("sp_get_max_queue_id")
    max_num = result["max_num"] if result and result["max_num"] else 0
    return f"Q{max_num + 1}"

def generate_notification_id():
    result = call_sp_one("sp_get_max_notification_id")
    max_num = result["max_num"] if result and result["max_num"] else 0
    return f"N{max_num + 1}"

def generate_vehicle_id():
    result = call_sp_one("sp_get_max_vehicle_id")
    max_num = result["max_num"] if result and result["max_num"] else 0
    return f"V{max_num + 1}"

@router.get("/driver/{driver_id}", response_class=HTMLResponse)
async def driver_dashboard(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    if not driver:
        return RedirectResponse(url="/login")
    notifications = call_sp("sp_get_unread_notifications", (driver_id,))
    call_sp("sp_mark_notifications_read", (driver_id,))
    vehicles = call_sp("sp_get_vehicles_by_driver", (driver_id,))
    queues = call_sp("sp_get_queues_by_driver", (driver_id,))
    return templates.TemplateResponse(request, "driver_dashboard.html", {
        "driver": driver,
        "notifications": notifications,
        "vehicle_count": len(vehicles),
        "queue_count": len(queues),
    })

@router.get("/driver/{driver_id}/queue", response_class=HTMLResponse)
async def driver_queue(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    vehicles = call_sp("sp_get_vehicles_by_driver", (driver_id,))
    queues = call_sp("sp_get_queues_by_driver", (driver_id,))
    my_queues = {q["vehicle_id"]: q for q in queues}
    return templates.TemplateResponse(request, "driver_queue.html", {
        "driver": driver,
        "vehicles": vehicles,
        "my_queues": my_queues,
    })

@router.get("/driver/{driver_id}/queue/register/{vehicle_id}", response_class=HTMLResponse)
async def register_queue(request: Request, driver_id: str, vehicle_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    vehicle = call_sp_one("sp_get_vehicle_by_id", (vehicle_id,))
    if not vehicle:
        return RedirectResponse(url=f"/driver/{driver_id}/queue")
    queues = call_sp("sp_get_queues_by_driver", (driver_id,))
    existing = next((q for q in queues if q["vehicle_id"] == vehicle_id), None)
    if existing:
        return RedirectResponse(url=f"/driver/{driver_id}/queue")
    if not has_enough_balance(driver_id):
        driver = get_driver(driver_id)
        return templates.TemplateResponse(request, "insufficient_balance.html", {
            "driver": driver,
            "queue_cost": QUEUE_COST
        })
    deduct_balance(driver_id)
    count_result = call_sp_one("sp_count_queue_by_type_stage", (vehicle["loader_type"], "selection"))
    position = count_result["cnt"] if count_result else 0
    queue_id = generate_queue_id()
    call_sp("sp_create_queue", (queue_id, driver_id, vehicle_id, vehicle["loader_type"], position, "selection"))
    return RedirectResponse(url=f"/driver/{driver_id}/queue", status_code=302)

@router.get("/driver/{driver_id}/cargo", response_class=HTMLResponse)
async def driver_cargo(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    vehicles = call_sp("sp_get_vehicles_by_driver", (driver_id,))
    cargos = call_sp("sp_get_all_cargos")
    queues = call_sp("sp_get_queues_by_driver", (driver_id,))
    my_loader_types = set(v["loader_type"] for v in vehicles)
    available_cargos = [c for c in cargos if c["status"] == "waiting" and c["loader_type"] in my_loader_types]
    ready_queues = [q for q in queues if q["position"] == 0 and q["stage"] == "selection"]
    return templates.TemplateResponse(request, "driver_cargo.html", {
        "driver": driver,
        "cargos": available_cargos,
        "ready_queues": ready_queues,
        "my_vehicles": vehicles,
    })

@router.get("/driver/{driver_id}/cargo/select/{cargo_id}/{vehicle_id}", response_class=HTMLResponse)
async def select_cargo(request: Request, driver_id: str, cargo_id: str, vehicle_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    cargo = call_sp_one("sp_get_cargo_by_id", (cargo_id,))
    vehicle = call_sp_one("sp_get_vehicle_by_id", (vehicle_id,))
    if cargo and vehicle:
        call_sp("sp_select_cargo", (cargo_id, driver_id, vehicle_id))
        call_sp("sp_update_vehicle_status", (vehicle_id, "busy"))
        call_sp("sp_delete_queue_by_driver_vehicle", (driver_id, vehicle_id))
        call_sp("sp_decrease_queue_position", (cargo["loader_type"], "selection"))
        count_result = call_sp_one("sp_count_queue_by_type_stage", (cargo["loader_type"], "loading"))
        position = count_result["cnt"] if count_result else 0
        queue_id = generate_queue_id()
        call_sp("sp_create_queue", (queue_id, driver_id, vehicle_id, cargo["loader_type"], position, "loading"))
    return RedirectResponse(url=f"/driver/{driver_id}/cargo", status_code=302)

@router.get("/driver/{driver_id}/vehicles", response_class=HTMLResponse)
async def driver_vehicles(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    vehicles = call_sp("sp_get_vehicles_by_driver", (driver_id,))
    return templates.TemplateResponse(request, "driver_vehicles.html", {
        "driver": driver,
        "vehicles": vehicles,
    })

@router.get("/driver/{driver_id}/vehicles/add", response_class=HTMLResponse)
async def driver_add_vehicle_page(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    return templates.TemplateResponse(request, "driver_vehicle_form.html", {"driver": driver, "error": None})

@router.post("/driver/{driver_id}/vehicles/add", response_class=HTMLResponse)
async def driver_add_vehicle_submit(
    request: Request,
    driver_id: str,
    smart_number: str = Form(...),
    plate: str = Form(...),
    loader_type: str = Form(...),
    model: str = Form(...)
):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    vehicles = call_sp("sp_get_all_vehicles")
    for v in vehicles:
        if v["smart_number"] == smart_number and v["plate"] != plate:
            return templates.TemplateResponse(request, "driver_vehicle_form.html", {
                "driver": driver,
                "error": "این شماره هوشمند قبلاً برای پلاک دیگری ثبت شده است"
            })
        if v["smart_number"] == smart_number and v["plate"] == plate and v["loader_type"] == loader_type:
            return templates.TemplateResponse(request, "driver_vehicle_form.html", {
                "driver": driver,
                "error": "این ماشین با همین نوع بارگیر قبلاً ثبت شده است"
            })
    vehicle_id = generate_vehicle_id()
    call_sp("sp_create_vehicle", (vehicle_id, smart_number, plate, loader_type, model, driver_id))
    return RedirectResponse(url=f"/driver/{driver_id}/vehicles", status_code=302)

@router.get("/driver/{driver_id}/history", response_class=HTMLResponse)
async def driver_history(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    cargos = call_sp("sp_get_all_cargos")
    vehicles = call_sp("sp_get_all_vehicles")
    vehicles_map = {v["id"]: v for v in vehicles}
    history = [c for c in cargos if c.get("driver_id") == driver_id and c.get("status") == "loaded"]
    for c in history:
        vehicle = vehicles_map.get(c.get("vehicle_id"), {})
        c["plate"] = vehicle.get("plate", "نامشخص")
    return templates.TemplateResponse(request, "driver_history.html", {"driver": driver, "history": history})

@router.get("/driver/{driver_id}/profile", response_class=HTMLResponse)
async def driver_profile(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    return templates.TemplateResponse(request, "driver_profile.html", {"driver": driver, "error": None, "success": None})

@router.post("/driver/{driver_id}/profile", response_class=HTMLResponse)
async def driver_profile_submit(
    request: Request,
    driver_id: str,
    full_name: str = Form(...),
    phone: str = Form(...),
    password: str = Form("")
):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    call_sp("sp_update_user", (driver_id, full_name, driver.get("national_id"), phone, password if password else driver["password"]))
    driver = get_driver(driver_id)
    return templates.TemplateResponse(request, "driver_profile.html", {"driver": driver, "error": None, "success": "اطلاعات با موفقیت ذخیره شد"})
