"""FastAPI application factory, router registration, exception handlers, lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import dispose_engine
from app.exceptions import AetherError
from app.middleware import RequestContextMiddleware
from app.routers import (
    audit,
    auth,
    documents,
    guidelines,
    health,
    patients,
    reasoning,
    records,
    safety,
)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Aether Clinician API",
        version="0.1.0",
        description="Clinician-facing diagnostic & management decision-support system (Phase 1).",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    @app.exception_handler(AetherError)
    async def aether_error_handler(_request: Request, exc: AetherError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    app.include_router(health.router)
    for module in (auth, patients, documents, records, safety, audit, reasoning, guidelines):
        app.include_router(module.router, prefix=API_PREFIX)

    return app


app = create_app()
