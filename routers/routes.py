from contextlib import asynccontextmanager
from math import sqrt

from fastapi import APIRouter, Request, FastAPI
from fastapi.responses import JSONResponse

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


def distance(point1: Coordinate, point2: Coordinate, scale: int) -> int:
    dx = (point2.longitude - point1.longitude) ** 2
    dy = (point2.latitude - point1.latitude) ** 2
    d = sqrt(dx + dy)
    d *= scale
    return int(d)


def generate_distance_matrix(mission: Mission) -> list[list[int]]:
    points: list[Coordinate] = [mission.start] + mission.waypoints
    matrix = [[distance(p1, p2, 100) for p2 in points] for p1 in points]
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
