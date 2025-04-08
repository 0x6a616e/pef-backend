from aiofiles import open as aiopen
from contextlib import asynccontextmanager
from math import pi, sin, cos, atan2, sqrt
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from time import time
from typing import BinaryIO

from fastapi import APIRouter, Request, FastAPI, UploadFile
from fastapi.responses import JSONResponse, Response

from ortools.constraint_solver import routing_enums_pb2, pywrapcp

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


def convert_to_degrees(value):
    def to_float(x):
        return float(x[0]) / float(x[1]) if isinstance(x, tuple) else float(x)

    try:
        d, m, s = value
        return to_float(d) + to_float(m) / 60 + to_float(s) / 3600
    except Exception:
        return None


def process_drone_image(file: BinaryIO) -> None:
    image = Image.open(file)

    optimal_size = (680, 382)
    resized_image = image.resize(optimal_size)

    exif = image._getexif()
    if not exif:
        return

    gps_data = {}
    for tag, value in exif.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "GPSInfo":
            for t in value:
                sub_decoded = GPSTAGS.get(t, t)
                gps_data[sub_decoded] = value[t]

    if "GPSLatitude" not in gps_data or "GPSLongitude" not in gps_data:
        return

    lat = convert_to_degrees(gps_data["GPSLatitude"])
    lng = convert_to_degrees(gps_data["GPSLongitude"])

    if lat is None or lng is None:
        return

    if gps_data.get("GPSLatitudeRef") == "S":
        lat = -lat
    if gps_data.get("GPSLongitudeRef") == "W":
        lng = -lng

    resized_image.save(f"images/drone_{time()}_{lat}_{lng}_.jpg")


@router.post("/uploadfile/{source}")
async def upload_file(source: str, file: UploadFile):
    if (source == "drone"):
        process_drone_image(file.file)
    else:
        filename: str = f"images/{source}_{time()}_.jpg"
        async with aiopen(filename, "wb") as of:
            while content := await file.read(1024):
                await of.write(content)

    return Response(status_code=200)
