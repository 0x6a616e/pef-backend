from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .internal.missions import router

app = FastAPI(
    title="PEF",
)
app.include_router(router.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
