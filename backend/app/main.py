"""App factory: CORS, table creation, eight routers (TDD §10, TDD-V2 §4.4). Under 40 lines."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.config import settings
from app.db import engine
from app.readiness import readiness
from app.routers import analyze, auth, courses, progress, project, roadmap, students, submit

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    SQLModel.metadata.create_all(engine)      # no migrations; drop tables by hand if a column changes
    yield


app = FastAPI(title="ANCHOR API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, courses, students, analyze, roadmap, progress, project, submit):
    app.include_router(module.router)


@app.get("/health")
def health() -> dict[str, object]:
    return readiness()
