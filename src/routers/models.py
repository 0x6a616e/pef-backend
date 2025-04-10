from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate
from uuid import UUID


class Mission(BaseModel):
    id: UUID
    start: Coordinate = None
    waypoints: list[Coordinate] = []


class ClassDistribution(BaseModel):
    agua:  float
    suelo_expuesto: float
    vegetacion_seca: float
    vegetacion_verde: float


class Result(BaseModel):
    image: str
    mask: str
    class_distribution: ClassDistribution
