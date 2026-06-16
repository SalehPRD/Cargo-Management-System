import json
import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin
from app.websocket import manager

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

QUEUE_FILE = "data/queues.json"
USERS_FILE = "data/users.json"
VEHICLES_FILE = "data/vehicles.json"
CARGOS_FILE = "data/cargos.json"
NOTIFICATIONS_FILE = "data/notifications.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_notification(driver_id, message):
    notifications = load_json(NOTIFICATIONS_FILE)
    notifications.append({
        "id": f"N{len(notifications)+1}",
        "driver_id": driver_id,
        "message": message,
        "read": False
    })
    save_json(NOTIFICATIONS_FILE, notifications)

@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    queues = load_json(QUEUE_FILE)
    users = load_json(USERS_FILE)
    vehicles = load_json(VEHICLES_FILE)
    drivers = {u["id"]: u for u in users if u.get("role") == "driver"}
    vehicles_map = {v["id"]: v for v in vehicles}
    queue_items = []
    for q in queues:
        driver = drivers.get(q["driver_id"], {})
        vehicle = vehicles_map.get(q["vehicle_id"], {})
        queue_items.append({
            **q,
            "driver_name": driver.get("full_name", "نامشخص"),
            "plate": vehicle.get("plate", "نامشخص"),
            "loader_type": vehicle.get("loader_type", "نامشخص"),
        })
    queue_items.sort(key=lambda x: x["position"])
    return templates.TemplateResponse(request, "queue.html", {"queue_items": queue_items})

@router.get("/pending", response_class=HTMLResponse)
async def pending_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargos = load_json(CARGOS_FILE)
    users = load_json(USERS_FILE)
    vehicles = load_json(VEHICLES_FILE)
    drivers = {u["id"]: u for u in users if u.get("role") == "driver"}
    vehicles_map = {v["id"]: v for v in vehicles}
    pending = []
    for c in cargos:
        if c.get("status") == "selected":
            driver = drivers.get(c.get("driver_id", ""), {})
            vehicle = vehicles_map.get(c.get("vehicle_id", ""), {})
            pending.append({
                **c,
                "driver_name": driver.get("full_name", "نامشخص"),
                "plate": vehicle.get("plate", "نامشخص"),
            })
    return templates.TemplateResponse(request, "pending.html", {"pending": pending})

@router.get("/pending/{cargo_id}/approve", response_class=HTMLResponse)
async def pending_approve(request: Request, cargo_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargos = load_json(CARGOS_FILE)
    vehicles = load_json(VEHICLES_FILE)
    queues = load_json(QUEUE_FILE)
    cargo = next((c for c in cargos if c["id"] == cargo_id), None)
    if cargo:
        driver_id = cargo.get("driver_id")
        vehicle_id = cargo.get("vehicle_id")
        cargo["status"] = "loaded"
        for v in vehicles:
            if v["id"] == vehicle_id:
                v["status"] = "free"
                break
        queues = [q for q in queues if not (q["driver_id"] == driver_id and q["stage"] == "loading")]
        for q in queues:
            if q.get("loader_type") == cargo.get("loader_type") and q["stage"] == "loading":
                q["position"] = max(0, q["position"] - 1)
                if q["position"] < 2:
                    msg = f"برای بارگیری بار {cargo.get('product_name','')} به مقصد {cargo.get('destination','')} به کارخانه مراجعه کنید. توجه: در صورت عدم مراجعه در ۳۰ دقیقه آینده، نوبت شما حذف خواهد شد"
                    sent = await manager.send_notification(q["driver_id"], msg)
                    if not sent:
                        add_notification(q["driver_id"], msg)
        save_json(CARGOS_FILE, cargos)
        save_json(VEHICLES_FILE, vehicles)
        save_json(QUEUE_FILE, queues)
    return RedirectResponse(url="/pending", status_code=302)

@router.get("/pending/{cargo_id}/cancel", response_class=HTMLResponse)
async def pending_cancel(request: Request, cargo_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargos = load_json(CARGOS_FILE)
    vehicles = load_json(VEHICLES_FILE)
    queues = load_json(QUEUE_FILE)
    cargo = next((c for c in cargos if c["id"] == cargo_id), None)
    if cargo:
        driver_id = cargo.get("driver_id")
        vehicle_id = cargo.get("vehicle_id")
        loader_type = cargo.get("loader_type")
        cancelled_vehicle = next((v for v in vehicles if v["id"] == vehicle_id), {})
        plate = cancelled_vehicle.get("plate", "")
        destination = cargo.get("destination", "")
        message = f"بار مربوط به پلاک {plate} با مقصد {destination} باطل شد"
        cargo["status"] = "waiting"
        cargo["driver_id"] = None
        cargo["vehicle_id"] = None
        for v in vehicles:
            if v["id"] == vehicle_id:
                v["status"] = "free"
                break
        queues = [q for q in queues if not (q["driver_id"] == driver_id and q["stage"] == "loading")]
        for q in queues:
            if q.get("loader_type") == loader_type and q["stage"] == "loading":
                q["position"] = max(1, q["position"] - 1)
        save_json(CARGOS_FILE, cargos)
        save_json(VEHICLES_FILE, vehicles)
        save_json(QUEUE_FILE, queues)
        sent = await manager.send_notification(driver_id, message)
        if not sent:
            add_notification(driver_id, message)
    return RedirectResponse(url="/pending", status_code=302)
