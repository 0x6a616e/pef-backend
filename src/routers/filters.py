from collections.abc import Callable

from .models import Result
from .utils import extract_coordinate, distance

Filter = Callable[[list[Result]], list[Result]]


def create_stack(*filters: Filter) -> Filter:
    def stack(results: list[Result]) -> list[Result]:
        for filter in filters:
            results = filter(results)
        return results
    return stack


def distribution_filter(results: list[Result]) -> list[Result]:
    filtered_results = []

    for result in results:
        agua = result.class_distribution.agua
        seca = result.class_distribution.vegetacion_seca
        verde = result.class_distribution.vegetacion_verde

        if agua > 40:
            continue
        if seca == 0 and verde == 0:
            continue
        filtered_results.append(result)

    return filtered_results


def distance_filter(results: list[Result]) -> list[Result]:
    def sort_function(result: Result) -> float:
        return result.class_distribution.vegetacion_seca

    filtered_results = []
    min_distance = 10

    copied_results = results
    copied_results.sort(reverse=True, key=sort_function)

    for result1 in copied_results:
        point1 = extract_coordinate(result1)
        to_add = True
        for result2 in filtered_results:
            point2 = extract_coordinate(result2)
            if distance(point1, point2) < min_distance:
                to_add = False
                break
        if to_add:
            filtered_results.append(result1)

    return filtered_results


DEFAULT_FILTER = create_stack(distribution_filter, distance_filter)
SOFT_FILTER = create_stack(distance_filter)
