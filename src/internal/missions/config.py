from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = str()
    images_folder: str = str()
    image_size: tuple[int, int] = tuple()


settings = Settings()
