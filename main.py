from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.websocket import manager

app = FastAPI(title="سامانه اعلام بار")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

from app.routes import auth, dashboard, cargo, users, vehicles, queue, admin, driver
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(cargo.router)
app.include_router(users.router)
app.include_router(vehicles.router)
app.include_router(queue.router)
app.include_router(admin.router)
app.include_router(driver.router)

@app.websocket("/ws/{driver_id}")
async def websocket_endpoint(websocket: WebSocket, driver_id: str):
    await manager.connect(driver_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(driver_id) 