from aiofiles import open as aiopen
from aiofiles.os import remove as airemove
from contextlib import asynccontextmanager
from cv2 import imread, imwrite, resize
from math import pi, sin, cos, atan2, sqrt
from time import time

from fastapi import APIRouter, Request, FastAPI, UploadFile
from fastapi.responses import JSONResponse, Response

from ortools.constraint_solver import routing_enums_pb2, pywrapcp

from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude


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


def distance(point1: Coordinate, point2: Coordinate) -> int:
    R = 6371e3
    phi1 = point1.latitude * pi / 180
    phi2 = point2.latitude * pi / 180
    diff_phi = (point2.latitude - point1.latitude) * pi / 180
    diff_gamma = (point2.longitude - point1.longitude) * pi / 180
    a = sin(diff_phi / 2) * sin(diff_phi / 2) + cos(phi1) * \
        cos(phi2) * sin(diff_gamma / 2) * sin(diff_gamma / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = R * c
    return int(d)


def generate_distance_matrix(mission: Mission) -> list[list[int]]:
    points: list[Coordinate] = [mission.start] + mission.waypoints
    matrix = [[distance(p1, p2) for p2 in points] for p1 in points]
    return matrix


def extract_route(manager, routing, solution) -> list[int]:
    index = routing.Start(0)
    route = [manager.IndexToNode(index)]
    while not routing.IsEnd(index):
        index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
    return route


def optimize_route(mission: Mission) -> Mission:
    matrix = generate_distance_matrix(mission)
    manager = pywrapcp.RoutingIndexManager(len(matrix), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 1

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        route: list[int] = extract_route(manager, routing, solution)
        waypoints: list[Coordinate] = []
        for i in route:
            if i != 0:
                waypoints.append(mission.waypoints[i - 1])
        mission.waypoints = waypoints

    return mission


@router.post("/edit", response_model=Mission)
async def edit_route(request: Request, mission: Mission):
    request.state.data["mission"] = optimize_route(mission)
    return JSONResponse(status_code=200, content=mission.model_dump())


@router.post("/uploadfile")
async def upload_file(lat: Latitude, lng: Longitude, file: UploadFile):
    tmp_file: str = f"images/tmp_{file.filename}"
    async with aiopen(tmp_file, "wb") as of:
        while content := await file.read(1024):
            await of.write(content)

    out_file: str = f"images/{lat}.{lng}.{time()}.jpg"
    resized_image = imread(tmp_file)
    resized_image = resize(resized_image, (680, 382))
    imwrite(out_file, resized_image)

    await airemove(tmp_file)

    return Response(status_code=200)
