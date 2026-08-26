"""App factory: CORS, table creation, five routers (docs/TDD.md §10). Keep this under 40 lines."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.config import settings
from app.db import engine
from app.routers import courses, progress, roadmap, students

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

app.include_router(courses.router)
app.include_router(students.router)
app.include_router(roadmap.router)
app.include_router(progress.router)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
