from fastapi import APIRouter, Request

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate


class Point(BaseModel):
    coordinate: Coordinate


class Route(BaseModel):
    points: list[Point] = []


router = APIRouter(
    prefix="/routes",
    tags=["routes"],
)


@router.get("/get", response_model=Route)
async def read_route(request: Request):
    route: Route = request.state.data["route"]
    return JSONResponse(status_code=200, content=route.model_dump())


@router.post("/edit", response_model=Route)
async def edit_route(request: Request, route: Route):
    request.state.data["route"] = route
    return JSONResponse(status_code=200, content=route.model_dump())
