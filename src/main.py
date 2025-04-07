from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import routes

origins = [
    "*",
]


app = FastAPI(
    title="PEF",
)
app.include_router(routes.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
