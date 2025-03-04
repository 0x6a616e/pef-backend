from fastapi import APIRouter, Request, FastAPI
from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate


class Mission(BaseModel):
    start: Coordinate = None
    waypoints: list[Coordinate] = []


@asynccontextmanager
async def lifespan(_: FastAPI):
    state = {
        "mission": Mission()
    }
    yield {"data": state}


router = APIRouter(
    prefix="/routes",
    tags=["routes"],
    lifespan=lifespan,
)


@router.get("/get", response_model=Mission)
async def read_route(request: Request):
    mission: Mission = request.state.data["mission"]
    return JSONResponse(status_code=200, content=mission.model_dump())


@router.post("/edit", response_model=Mission)
async def edit_route(request: Request, mission: Mission):
    request.state.data["mission"] = mission
    return JSONResponse(status_code=200, content=mission.model_dump())
