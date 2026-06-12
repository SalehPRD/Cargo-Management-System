import json
import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

USERS_FILE = "data/users.json"
CARGOS_FILE = "data/cargos.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    users = load_json(USERS_FILE)
    cargos = load_json(CARGOS_FILE)
    
    stats = {
        "total_cargos": len(cargos),
        "waiting": len([c for c in cargos if c.get("status") == "waiting"]),
        "loaded": len([c for c in cargos if c.get("status") == "loaded"]),
        "in_progress": len([c for c in cargos if c.get("status") == "selected"]),
        "total_drivers": len([u for u in users if u.get("role") == "driver"]),
    }
    
    return templates.TemplateResponse(request, "dashboard.html", {"stats": stats})