from collections.abc import Callable

from .config import settings
from .models import Result, SegmentationClass
from .routing import distance


Filter = Callable[[list[Result]], list[Result]]


def compose(filters: list[Filter]) -> Filter:
    def s(rs: list[Result]) -> list[Result]:
        for f in filters:
            rs = f(rs)
        return rs
    return s


def less_than(field: SegmentationClass, value: int):
    def c(rs: list[Result]) -> list[Result]:
        results = []
        for r in rs:
            if r.distribution[field] <= value:
                results.append(r)
        return results
    return c


def greater_than(field: SegmentationClass, value: int):
    def c(rs: list[Result]) -> list[Result]:
        results = []
        for r in rs:
            if r.distribution[field] >= value:
                results.append(r)
        return results
    return c


def distance_filter(results: list[Result]) -> list[Result]:
    def sort_key(r: Result) -> float:
        return r.distribution.get(SegmentationClass.VEGETACION_SECA, 0)

    filtered_results: list[Result] = []

    copied_results = results
    copied_results.sort(reverse=True, key=sort_key)

    for result_1 in copied_results:
        point1 = result_1.coordinate
        to_add = True
        for result_2 in filtered_results:
            point2 = result_2.coordinate
            if distance(point1, point2) < settings.min_distance:
                to_add = False
                break
        if to_add:
            filtered_results.append(result_1)

    return filtered_results
