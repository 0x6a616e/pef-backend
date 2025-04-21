from math import pi, sin, cos, atan2, sqrt
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude
from ortools.constraint_solver import routing_enums_pb2, pywrapcp

from .config import settings
from .models import Mission


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
    points = [mission.start] + mission.waypoints
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
        route = extract_route(manager, routing, solution)
        waypoints: list[Coordinate] = []
        for i in route:
            if i != 0:
                waypoints.append(mission.waypoints[i - 1])
        mission.waypoints = waypoints

    return mission


def middle_point(point1: Coordinate, point2: Coordinate) -> Coordinate:
    lng = Longitude((point1.longitude + point2.longitude) / 2)
    lat = Latitude((point1.latitude + point2.latitude) / 2)
    return Coordinate(latitude=lat, longitude=lng)


def divide_line(points: list[Coordinate], idx1: int, idx2: int) -> None:
    point1 = points[idx1]
    point2 = points[idx2]
    if (distance(point1, point2) < settings.min_distance):
        return
    middle = middle_point(point1, point2)
    points.insert(idx2, middle)
    divide_line(points, idx2, idx2 + 1)
    divide_line(points, idx1, idx2)


def process_area(points: list[Coordinate]) -> list[Coordinate]:
    lats = []
    lngs = []
    for point in points:
        lats.append(point.latitude)
        lngs.append(point.longitude)
    lats.sort()
    lngs.sort()
    ul = Coordinate(latitude=lats[-1], longitude=lngs[0])
    ur = Coordinate(latitude=lats[-1], longitude=lngs[-1])
    bl = Coordinate(latitude=lats[0], longitude=lngs[0])
    br = Coordinate(latitude=lats[0], longitude=lngs[-1])
    ll = [bl, ul]
    rl = [br, ur]
    divide_line(ll, 0, 1)
    divide_line(rl, 0, 1)
    proccesed_list = [item for pair in zip(ll, rl) for item in pair]
    return proccesed_list
