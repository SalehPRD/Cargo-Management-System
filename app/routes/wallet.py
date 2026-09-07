from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import get_session
from app.database import call_sp, call_sp_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

QUEUE_COST = 1000000

def get_driver(driver_id):
    return call_sp_one("sp_get_user_by_id", (driver_id,))

def get_balance(driver_id):
    driver = get_driver(driver_id)
    return driver.get("balance", 0) if driver else 0

def has_enough_balance(driver_id):
    return get_balance(driver_id) >= QUEUE_COST

def deduct_balance(driver_id):
    call_sp("sp_deduct_balance", (driver_id, QUEUE_COST))

def add_balance(driver_id, amount):
    call_sp("sp_update_balance", (driver_id, amount))

@router.get("/driver/{driver_id}/wallet", response_class=HTMLResponse)
async def wallet_page(request: Request, driver_id: str):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    return templates.TemplateResponse(request, "wallet.html", {
        "driver": driver,
        "balance": get_balance(driver_id),
        "queue_cost": QUEUE_COST
    })

@router.post("/driver/{driver_id}/wallet/charge", response_class=HTMLResponse)
async def wallet_charge(request: Request, driver_id: str, amount: int = Form(...)):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    driver = get_driver(driver_id)
    return templates.TemplateResponse(request, "payment_gateway.html", {
        "driver": driver,
        "amount": amount,
        "driver_id": driver_id
    })

@router.post("/driver/{driver_id}/wallet/pay", response_class=HTMLResponse)
async def wallet_pay(request: Request, driver_id: str, amount: int = Form(...)):
    session = get_session(request)
    if not session or session["id"] != driver_id:
        return RedirectResponse(url="/login")
    add_balance(driver_id, amount)
    driver = get_driver(driver_id)
    return templates.TemplateResponse(request, "payment_success.html", {
        "driver": driver,
        "amount": amount,
        "balance": get_balance(driver_id)
    })
