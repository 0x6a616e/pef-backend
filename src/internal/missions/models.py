from enum import StrEnum
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate


class SegmentationClass(StrEnum):
    FONDO = "0"
    AGUA = "1"
    SUELO_EXPUESTO = "2"
    VEGETACION_SECA = "3"
    VEGETACION_VERDE = "4"

    @property
    def int_value(self):
        return int(self.value)


class Mission(BaseModel):
    id: str = ""
    start: Coordinate = None
    waypoints: list[Coordinate] = []


class Result(BaseModel):
    image: str
    mask: str
    distribution: dict[SegmentationClass, float]
