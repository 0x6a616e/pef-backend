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
    def color(self) -> str:
        match self:
            case SegmentationClass.FONDO:
                return "#000000"
            case SegmentationClass.AGUA:
                return "#004fff"
            case SegmentationClass.SUELO_EXPUESTO:
                return "#ffffff"
            case SegmentationClass.VEGETACION_SECA:
                return "#8f9107"
            case SegmentationClass.VEGETACION_VERDE:
                return "#08920a"


class Result(BaseModel):
    image: str
    mask: str
    distribution: dict[SegmentationClass, float]


class Mission(BaseModel):
    id: str
    start: Coordinate | None = None
    waypoints: list[Coordinate] = []
    results: list[Result] = []
