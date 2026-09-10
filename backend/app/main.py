from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import SessionLocal
from app.routers import admin, auth, competitions, public
from app.seed import seed_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        seed_admin(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="OlympicAI Scoring API", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api_prefix = "/api/v1"
    application.include_router(auth.router, prefix=api_prefix)
    application.include_router(admin.router, prefix=api_prefix)
    application.include_router(competitions.router, prefix=api_prefix)
    application.include_router(public.router, prefix=api_prefix)

    @application.get("/healthz", tags=["health"])
    def healthz() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
