from collections.abc import Callable

from .config import settings
from .models import Result, SegmentationClass
from .routing import distance

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
        agua = result.distribution.get(SegmentationClass.AGUA, 0)
        seca = result.distribution.get(SegmentationClass.VEGETACION_SECA, 0)
        verde = result.distribution.get(SegmentationClass.VEGETACION_VERDE, 0)

        if agua > 40:
            continue
        if seca == 0 and verde == 0:
            continue
        filtered_results.append(result)

    return filtered_results


def distance_filter(results: list[Result]) -> list[Result]:
    def sort_key(result: Result) -> float:
        return result.distribution.get(SegmentationClass.VEGETACION_SECA, 0)

    filtered_results: list[Result] = []
    min_distance = 15

    copied_results = results
    copied_results.sort(reverse=True, key=sort_key)

    for result_1 in copied_results:
        point1 = result_1.coordinate
        to_add = True
        for result_2 in filtered_results:
            point2 = result_2.coordinate
            if distance(point1, point2) < min_distance:
                to_add = False
                break
        if to_add:
            filtered_results.append(result_1)

    return filtered_results


DEFAULT_FILTER = create_stack(distribution_filter, distance_filter)
SOFT_FILTER = create_stack(distance_filter)
