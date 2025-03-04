from contextlib import asynccontextmanager
from fastapi import FastAPI

from .routers import routes


@asynccontextmanager
async def lifespan(_: FastAPI):
    state = {
        "route": routes.Route()
    }
    yield {"data": state}


app = FastAPI(
    title="PEF",
    lifespan=lifespan
)
app.include_router(routes.router)
