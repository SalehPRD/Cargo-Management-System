import json
import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

USERS_FILE = "data/users.json"
VEHICLES_FILE = "data/vehicles.json"
CARGOS_FILE = "data/cargos.json"
QUEUE_FILE = "data/queues.json"
NOTIFICATIONS_FILE = "data/notifications.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_driver(driver_id):
    users = load_json(USERS_FILE)
    return next((u for u in users if u["id"] == driver_id), None)

def get_notifications(driver_id):
    notifications = load_json(NOTIFICATIONS_FILE)
    return [n for n in notifications if n["driver_id"] == driver_id and not n["read"]]

def mark_notifications_read(driver_id):
    notifications = load_json(NOTIFICATIONS_FILE)
    for n in notifications:
        if n["driver_id"] == driver_id:
            n["read"] = True
    save_json(NOTIFICATIONS_FILE, notifications)

@router.get("/driver/{driver_id}", response_class=HTMLResponse)
async def driver_dashboard(request: Request, driver_id: str):
    driver = get_driver(driver_id)
    if not driver:
        return RedirectResponse(url="/login")
    notifications = get_notifications(driver_id)
    mark_notifications_read(driver_id)
    vehicles = [v for v in load_json(VEHICLES_FILE) if v["driver_id"] == driver_id]
    queues = [q for q in load_json(QUEUE_FILE) if q["driver_id"] == driver_id]
    return templates.TemplateResponse(request, "driver_dashboard.html", {
        "driver": driver,
        "notifications": notifications,
        "vehicle_count": len(vehicles),
        "queue_count": len(queues),
    })

@router.get("/driver/{driver_id}/queue", response_class=HTMLResponse)
async def driver_queue(request: Request, driver_id: str):
    driver = get_driver(driver_id)
    vehicles = load_json(VEHICLES_FILE)
    queues = load_json(QUEUE_FILE)
    my_vehicles = [v for v in vehicles if v["driver_id"] == driver_id]
    my_queues = {q["vehicle_id"]: q for q in queues if q["driver_id"] == driver_id}
    return templates.TemplateResponse(request, "driver_queue.html", {
        "driver": driver,
        "vehicles": my_vehicles,
        "my_queues": my_queues,
    })

@router.get("/driver/{driver_id}/queue/register/{vehicle_id}", response_class=HTMLResponse)
async def register_queue(request: Request, driver_id: str, vehicle_id: str):
    queues = load_json(QUEUE_FILE)
    vehicles = load_json(VEHICLES_FILE)

    vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)
    if not vehicle:
        return RedirectResponse(url=f"/driver/{driver_id}/queue")

    existing = next((q for q in queues if q["vehicle_id"] == vehicle_id and q["driver_id"] == driver_id), None)
    if existing:
        return RedirectResponse(url=f"/driver/{driver_id}/queue")

    same_type = [q for q in queues if q.get("loader_type") == vehicle["loader_type"] and q["stage"] == "selection"]
    position = len(same_type)

    queues.append({
        "id": f"Q{len(queues)+1}",
        "driver_id": driver_id,
        "vehicle_id": vehicle_id,
        "loader_type": vehicle["loader_type"],
        "position": position,
        "stage": "selection"
    })
    save_json(QUEUE_FILE, queues)
    return RedirectResponse(url=f"/driver/{driver_id}/queue", status_code=302)

@router.get("/driver/{driver_id}/cargo", response_class=HTMLResponse)
async def driver_cargo(request: Request, driver_id: str):
    driver = get_driver(driver_id)
    vehicles = load_json(VEHICLES_FILE)
    cargos = load_json(CARGOS_FILE)
    queues = load_json(QUEUE_FILE)

    my_vehicles = [v for v in vehicles if v["driver_id"] == driver_id]
    my_loader_types = set(v["loader_type"] for v in my_vehicles)

    available_cargos = [c for c in cargos if c["status"] == "waiting" and c["loader_type"] in my_loader_types]

    ready_queues = [q for q in queues if q["driver_id"] == driver_id and q["position"] == 0 and q["stage"] == "selection"]

    return templates.TemplateResponse(request, "driver_cargo.html", {
        "driver": driver,
        "cargos": available_cargos,
        "ready_queues": ready_queues,
        "my_vehicles": my_vehicles,
    })

@router.get("/driver/{driver_id}/cargo/select/{cargo_id}/{vehicle_id}", response_class=HTMLResponse)
async def select_cargo(request: Request, driver_id: str, cargo_id: str, vehicle_id: str):
    cargos = load_json(CARGOS_FILE)
    vehicles = load_json(VEHICLES_FILE)
    queues = load_json(QUEUE_FILE)

    cargo = next((c for c in cargos if c["id"] == cargo_id), None)
    vehicle = next((v for v in vehicles if v["id"] == vehicle_id), None)

    if cargo and vehicle:
        cargo["status"] = "selected"
        cargo["driver_id"] = driver_id
        cargo["vehicle_id"] = vehicle_id
        vehicle["status"] = "busy"

        queues = [q for q in queues if not (q["driver_id"] == driver_id and q["vehicle_id"] == vehicle_id and q["stage"] == "selection")]

        loading_same_type = [q for q in queues if q.get("loader_type") == cargo["loader_type"] and q["stage"] == "loading"]
        position = len(loading_same_type)

        queues.append({
            "id": f"Q{len(queues)+1}",
            "driver_id": driver_id,
            "vehicle_id": vehicle_id,
            "loader_type": cargo["loader_type"],
            "position": position,
            "stage": "loading"
        })

        for q in queues:
            if q.get("loader_type") == cargo["loader_type"] and q["stage"] == "selection":
                q["position"] = max(0, q["position"] - 1)

        save_json(CARGOS_FILE, cargos)
        save_json(VEHICLES_FILE, vehicles)
        save_json(QUEUE_FILE, queues)

    return RedirectResponse(url=f"/driver/{driver_id}/cargo", status_code=302)

@router.get("/driver/{driver_id}/vehicles", response_class=HTMLResponse)
async def driver_vehicles(request: Request, driver_id: str):
    driver = get_driver(driver_id)
    vehicles = [v for v in load_json(VEHICLES_FILE) if v["driver_id"] == driver_id]
    return templates.TemplateResponse(request, "driver_vehicles.html", {
        "driver": driver,
        "vehicles": vehicles,
    })

@router.get("/driver/{driver_id}/vehicles/add", response_class=HTMLResponse)
async def driver_add_vehicle_page(request: Request, driver_id: str):
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
    vehicles = load_json(VEHICLES_FILE)
    driver = get_driver(driver_id)

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
    save_json(VEHICLES_FILE, vehicles)
    return RedirectResponse(url=f"/driver/{driver_id}/vehicles", status_code=302)

@router.get("/driver/{driver_id}/profile", response_class=HTMLResponse)
async def driver_profile(request: Request, driver_id: str):
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
    users = load_json(USERS_FILE)
    for u in users:
        if u["id"] == driver_id:
            u["full_name"] = full_name
            u["phone"] = phone
            if password:
                u["password"] = password
            break
    save_json(USERS_FILE, users)
    driver = get_driver(driver_id)
    return templates.TemplateResponse(request, "driver_profile.html", {"driver": driver, "error": None, "success": "اطلاعات با موفقیت ذخیره شد"})
@router.get("/driver/{driver_id}/history", response_class=HTMLResponse)
async def driver_history(request: Request, driver_id: str):
    driver = get_driver(driver_id)
    cargos = load_json(CARGOS_FILE)
    vehicles = load_json(VEHICLES_FILE)
    vehicles_map = {v["id"]: v for v in vehicles}
    history = [c for c in cargos if c.get("driver_id") == driver_id and c.get("status") == "loaded"]
    for c in history:
        vehicle = vehicles_map.get(c.get("vehicle_id"), {})
        c["plate"] = vehicle.get("plate", "نامشخص")
    return templates.TemplateResponse(request, "driver_history.html", {"driver": driver, "history": history})