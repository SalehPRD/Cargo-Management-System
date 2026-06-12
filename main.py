from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="سامانه اعلام بار")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

from app.routes import auth, dashboard, cargo
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(cargo.router)