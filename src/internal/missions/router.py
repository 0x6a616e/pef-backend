from aiofiles import open as aiopen
from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from json import loads
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from pydantic import TypeAdapter
from os import mkdir
from os.path import exists
from time import time
from typing import BinaryIO
from uuid import uuid4
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from pydantic_extra_types.coordinate import Coordinate

from .ai import segment_folder_images
from .filters import DEFAULT_FILTER, SOFT_FILTER
from .models import Mission, Result
from .utils import optimize_route, extract_coordinate
from .database import query_current_mission, insert_mission, update_mission
from .models import Mission
from .routing import optimize_route


# Change this section
IMAGES_FOLDER = "images"
RESULTS_FILENAME = "resultados.json"
CURRENT_MISSION = Mission(id=uuid4().hex)

router = APIRouter(
    prefix="/routes",
    tags=["routes"],
    prefix="/missions",
    tags=["missions"]
)


@router.post("/initialize")
async def initialize_missions(start: Coordinate):
    mission = Mission(
        start=start,
        foldername=uuid4().hex
    )
    await insert_mission(mission)
    return Response(status_code=200)


@router.get("/get", response_model=Mission)
async def get_current_mission():
    mission = await query_current_mission()
    if mission is None:
        return Response(status_code=502)

    return JSONResponse(status_code=200, content=mission.model_dump())


@router.post("/edit", response_model=Mission)
async def edit_route(mission: Mission):
    current_mission = await query_current_mission()
    if current_mission is None:
        return Response(status_code=502)

def convert_to_degrees(value):
    def to_float(x):
        return float(x[0]) / float(x[1]) if isinstance(x, tuple) else float(x)

    try:
        d, m, s = value
        return to_float(d) + to_float(m) / 60 + to_float(s) / 3600
    except Exception:
        return None


def process_drone_image(file: BinaryIO) -> None:
    global IMAGES_FOLDER
    global RESULTS_FILENAME
    global CURRENT_MISSION

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

    path = f"{IMAGES_FOLDER}/{CURRENT_MISSION.id}"
    filename = f"drone_{time()}_{lat}_{lng}_.jpg"

    resized_image.save(f"{path}/{filename}")


@router.post("/uploadfile/{source}")
async def upload_file(source: str, file: UploadFile):
    global IMAGES_FOLDER
    global RESULTS_FILENAME
    global CURRENT_MISSION

    path = f"{IMAGES_FOLDER}/{CURRENT_MISSION.id}"
    if not exists(path):
        mkdir(path)
    if (source == "drone"):
        process_drone_image(file.file)
    else:
        filename: str = f"{source}_{time()}_.jpg"
        async with aiopen(f"{path}/{filename}", "wb") as of:
            while content := await file.read(1024):
                await of.write(content)

    return Response(status_code=200)


@router.get("/process")
async def process():
    global IMAGES_FOLDER
    global RESULTS_FILENAME
    global CURRENT_MISSION

    results = segment_folder_images(CURRENT_MISSION.id)
    if not results:
        return Response(status_code=500)
    print(results)
    filtered_results = DEFAULT_FILTER(results)
    if len(filtered_results) == 0:
        filtered_results = SOFT_FILTER(results)
    mission = CURRENT_MISSION
    mission.id = uuid4().hex
    for result in filtered_results:
        coord = extract_coordinate(result)
        mission.waypoints.append(coord)
    CURRENT_MISSION = mission
    return JSONResponse(status_code=200, content=CURRENT_MISSION.model_dump())
