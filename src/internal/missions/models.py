from enum import StrEnum
from typing import Annotated
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude


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

    @property
    def coordinate(self) -> Coordinate:
        filedata = self.image.split("_")
        lat = Latitude(filedata[2])
        lng = Longitude(filedata[3])
        return Coordinate(latitude=lat, longitude=lng)


PyObjectId = Annotated[str, BeforeValidator(str)]


class Mission(BaseModel):
    id: PyObjectId | None = Field(alias="_id", default=None)
    foldername: str = ""
    start: Coordinate
    waypoints: list[Coordinate] = []
    results: list[Result] = []

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )
