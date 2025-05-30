from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = ""
    images_folder: str = ""
    mongo_url: str = ""
    image_size: tuple[int, int] = (680, 382)
    min_distance: int = 15
    waypoint_limit: int = 99


settings = Settings()
