from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_admin
from app.database import call_sp, call_sp_one
from app.websocket import manager

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def generate_notification_id():
    result = call_sp_one("sp_get_max_notification_id")
    max_num = result["max_num"] if result and result["max_num"] else 0
    return f"N{max_num + 1}"

async def add_notification(driver_id, message):
    notif_id = generate_notification_id()
    call_sp("sp_create_notification", (notif_id, driver_id, message))

@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    queues = call_sp("sp_get_all_queues")
    users = call_sp("sp_get_all_users")
    vehicles = call_sp("sp_get_all_vehicles")
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
    cargos = call_sp("sp_get_pending_cargos")
    users = call_sp("sp_get_all_users")
    vehicles = call_sp("sp_get_all_vehicles")
    drivers = {u["id"]: u for u in users if u.get("role") == "driver"}
    vehicles_map = {v["id"]: v for v in vehicles}
    pending = []
    for c in cargos:
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
    cargo = call_sp_one("sp_get_cargo_by_id", (cargo_id,))
    if cargo:
        driver_id = cargo.get("driver_id")
        vehicle_id = cargo.get("vehicle_id")
        loader_type = cargo.get("loader_type")
        call_sp("sp_load_cargo", (cargo_id,))
        call_sp("sp_update_vehicle_status", (vehicle_id, "free"))
        call_sp("sp_delete_queue_by_driver_stage", (driver_id, "loading"))
        call_sp("sp_decrease_queue_position", (loader_type, "loading"))
        queues = call_sp("sp_get_all_queues")
        for q in queues:
            if q.get("loader_type") == loader_type and q["stage"] == "loading" and q["position"] < 2:
                msg = f"برای بارگیری بار {cargo.get('product_name','')} به مقصد {cargo.get('destination','')} به کارخانه مراجعه کنید. توجه: در صورت عدم مراجعه در ۳۰ دقیقه آینده، نوبت شما حذف خواهد شد"
                sent = await manager.send_notification(q["driver_id"], msg)
                if not sent:
                    await add_notification(q["driver_id"], msg)
    return RedirectResponse(url="/pending", status_code=302)

@router.get("/pending/{cargo_id}/cancel", response_class=HTMLResponse)
async def pending_cancel(request: Request, cargo_id: str):
    if not require_admin(request):
        return RedirectResponse(url="/login")
    cargo = call_sp_one("sp_get_cargo_by_id", (cargo_id,))
    if cargo:
        driver_id = cargo.get("driver_id")
        vehicle_id = cargo.get("vehicle_id")
        loader_type = cargo.get("loader_type")
        vehicle = call_sp_one("sp_get_vehicle_by_id", (vehicle_id,))
        plate = vehicle.get("plate", "") if vehicle else ""
        message = f"بار مربوط به پلاک {plate} با مقصد {cargo.get('destination', '')} باطل شد"
        call_sp("sp_cancel_cargo", (cargo_id,))
        call_sp("sp_update_vehicle_status", (vehicle_id, "free"))
        call_sp("sp_delete_queue_by_driver_stage", (driver_id, "loading"))
        call_sp("sp_decrease_queue_position", (loader_type, "loading"))
        sent = await manager.send_notification(driver_id, message)
        if not sent:
            await add_notification(driver_id, message)
    return RedirectResponse(url="/pending", status_code=302)
