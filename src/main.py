from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "ids": id_list
        }
    )
