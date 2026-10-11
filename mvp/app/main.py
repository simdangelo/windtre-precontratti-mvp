from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import api, pages
from app.bootstrap import bootstrap_database
from app.database import engine
from app.services.exceptions import (
    DomainNotFoundError,
    DomainValidationError,
    GenerationError,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    bootstrap_database()
    yield
    engine.dispose()


app = FastAPI(title="MVP Sintesi & Trasparenze", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(DomainNotFoundError)
async def not_found_handler(_request: Request, exc: DomainNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DomainValidationError)
async def validation_handler(_request: Request, exc: DomainValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(GenerationError)
async def generation_handler(_request: Request, exc: GenerationError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.include_router(pages.router)
app.include_router(api.router, prefix="/api")
