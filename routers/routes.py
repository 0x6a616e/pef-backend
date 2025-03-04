from fastapi import APIRouter, Request, FastAPI
from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate


class Point(BaseModel):
    coordinate: Coordinate


class Route(BaseModel):
    points: list[Point] = []


@asynccontextmanager
async def lifespan(_: FastAPI):
    state = {
        "route": Route()
    }
    yield {"data": state}


router = APIRouter(
    prefix="/routes",
    tags=["routes"],
    lifespan=lifespan,
)


@router.get("/get", response_model=Route)
async def read_route(request: Request):
    route: Route = request.state.data["route"]
    return JSONResponse(status_code=200, content=route.model_dump())


@router.post("/edit", response_model=Route)
async def edit_route(request: Request, route: Route):
    request.state.data["route"] = route
    return JSONResponse(status_code=200, content=route.model_dump())
