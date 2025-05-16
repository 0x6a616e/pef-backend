from bson import ObjectId
import motor.motor_asyncio

from .config import settings
from .models import Mission

client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_url)
db = client.get_database("pef")
mission_collection = db.get_collection("missions")


async def query_current_mission() -> Mission | None:
    mission = await mission_collection.find_one(sort=[("_id", -1)])
    if mission is not None:
        mission = Mission.model_validate(mission)

    return mission


async def query_mission(id: str) -> Mission | None:
    mission = await mission_collection.find_one({"_id": ObjectId(id)})
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
        {"_id": ObjectId(mission.id)},
        {"$set": mission.model_dump(exclude={"id"})},
    )


async def query_mission_list() -> list[str]:
    cursor = mission_collection.find(sort=[("_id", -1)])
    id_list = []
    async for mission in cursor:
        if mission["results"]:
            id_list.append(str(mission["_id"]))
    return id_list
