from fastapi import FastAPI

from .routers import routes


app = FastAPI(
    title="PEF",
)
app.include_router(routes.router)
