import aiofiles
from fastapi import APIRouter, Response, UploadFile
from fastapi.responses import JSONResponse
import os
from PIL import Image, ExifTags
from PIL.ExifTags import GPSTAGS
from pydantic_extra_types.coordinate import Coordinate
from time import time
from typing import BinaryIO
from uuid import uuid4

from .config import settings
from .database import query_current_mission, insert_mission, update_mission
from .filters import compose, greater_than, less_than, distance_filter
from .models import Mission, SegmentationClass
from .routing import optimize_route, process_area
from .segmentation import segment_folder


router = APIRouter()


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

    current_mission.waypoints = mission.waypoints
    current_mission = optimize_route(current_mission)
    await update_mission(current_mission)
    return JSONResponse(status_code=200, content=current_mission.model_dump())


@router.post("/area")
async def handle_area(mission: Mission):
    current_mission = await query_current_mission()
    if current_mission is None:
        return Response(status_code=502)

    current_mission.waypoints = process_area(mission.waypoints)
    await update_mission(current_mission)
    return JSONResponse(status_code=200, content=current_mission.model_dump())


async def process_drone_image(file: BinaryIO) -> None:
    def convert_to_degrees(value):
        def to_float(x):
            return float(x[0]) / float(x[1]) if isinstance(x, tuple) else float(x)

        try:
            d, m, s = value
            return to_float(d) + to_float(m) / 60 + to_float(s) / 3600
        except Exception:
            return None

    image = Image.open(file)

    optimal_size = settings.image_size
    resized_image = image.resize(optimal_size)

    exif = image.getexif()
    if not exif:
        return

    gps_data = {}
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
    for k in gps_ifd:
        sub_decoded = GPSTAGS.get(k, k)
        gps_data[sub_decoded] = gps_ifd[k]

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

    current_mission = await query_current_mission()
    if current_mission is None:
        return
    filename = f"drone_{time()}_{lat}_{lng}_.jpg"
    fullpath = os.path.join(
        settings.images_folder,
        current_mission.foldername,
        filename
    )

    resized_image.save(fullpath)


@router.post("/uploadfile/{source}")
async def upload_file(source: str, file: UploadFile):
    current_mission = await query_current_mission()
    if current_mission is None:
        return Response(status_code=502)

    path = os.path.join(
        settings.images_folder,
        current_mission.foldername
    )

    if not os.path.exists(path):
        os.mkdir(path)
    if (source == "drone"):
        await process_drone_image(file.file)
    else:
        filename: str = f"{source}_{time()}_.jpg"
        async with aiofiles.open(f"{path}/{filename}", "wb") as of:
            while content := await file.read(1024):
                await of.write(content)

    return Response(status_code=200)


@router.post("/process")
async def process(params: dict[SegmentationClass, int]):
    filters = []
    for field, value in params.items():
        if value > 0:
            filters.append(greater_than(field, value))
        elif value < 0:
            filters.append(less_than(field, -1 * value))
    filters.append(distance_filter)
    filter = compose(filters)

    current_mission = await query_current_mission()
    if current_mission is None:
        return Response(status_code=502)

    results = segment_folder(current_mission.foldername)
    if not results:
        return Response(status_code=502)

    results = filter(results)

    current_mission.results = results
    await update_mission(current_mission)

    new_mission = Mission(
        start=current_mission.start,
        foldername=uuid4().hex
    )
    new_mission.waypoints.extend((r.coordinate for r in results))
    new_mission = optimize_route(new_mission)
    await insert_mission(new_mission)
    return JSONResponse(status_code=200, content=new_mission.model_dump())
