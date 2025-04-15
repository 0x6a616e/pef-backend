from bson import ObjectId
import motor.motor_asyncio

from .config import settings
from .models import Mission

client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_url)
db = client.get_database("pef")
mission_collection = db.get_collection("missions")


async def get_current_mission() -> Mission | None:
    mission = await mission_collection.find_one(
        {},
        {},
        {"$sort": {"_id": -1}}
    )
    if mission is not None:
        mission = Mission.model_validate(mission)

    return mission


async def insert_mission(mission: Mission) -> None:
    await mission_collection.insert_one(
        mission.model_dump(
            exclude={"id"},
        )
    )


async def update_mission(mission: Mission) -> None:
    await mission_collection.find_one_and_update(
        {"_id": ObjectId},
        {"$set": mission.model_dump(exclude={"id"})},
    )
