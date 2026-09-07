"""
FastAPI Application Entry Point.
Configures CORS middleware, lifespan events, and mounts API routers.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as core_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown event lifecycle handler."""
    # Future: init DB pools, start background scheduler, setup logging
    yield
    # Future: teardown DB pools, stop scheduler


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="ORCA — Marine Intelligence Platform API",
        description="Multi-Agent Marine Intelligence & Safety Hub for SIH 2026 under ISRO",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration — allow frontend dev origins and configured origins
    origins = list(settings.BACKEND_CORS_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount top-level /api endpoints (health, query, safety-check)
    app.include_router(core_router)

    # Mount existing v1 sub-routers only if all optional deps are available.
    # This prevents import errors when structlog/shapely/apscheduler are not yet installed.
    try:
        from app.api.router import api_router
        app.include_router(api_router)
    except ImportError:
        pass

    return app


app = create_app()
