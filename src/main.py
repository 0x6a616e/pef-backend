from bson import ObjectId
from dateutil import tz
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os

from .internal.missions.config import settings
from .internal.missions.database import query_mission_list, query_mission
from .internal.missions.router import router as mission_router

app = FastAPI(
    title="PEF",
)
app.include_router(
    mission_router,
    prefix="/api/missions",
    tags=["api/missions"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


templates = Jinja2Templates(directory="src/templates")


@app.get("/image/{folder}/{filename}", response_class=FileResponse)
async def get_image(folder: str, filename: str):
    filepath = os.path.join(
        settings.images_folder,
        folder,
        filename
    )
    return filepath


@app.get("/map/{mission_id}", response_class=HTMLResponse)
async def get_map(request: Request, mission_id: str):
    mission = await query_mission(mission_id)
    if mission is None:
        return Response(status_code=502)

    return templates.TemplateResponse(
        request=request,
        name="map.html",
        context={
            "mission": mission
        }
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    id_list = await query_mission_list()
    local_tz = tz.gettz("America/Monterrey")
    proccesed_list = []
    for id in id_list:
        t = ObjectId(id).generation_time.astimezone(
            local_tz).strftime("%d/%m/%y - %H:%M")
        proccesed_list.append((id, t))

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data_list": proccesed_list[1:]
        }
    )
