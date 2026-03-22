from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


settings = get_settings()
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)


def _should_log_request_timing(path: str) -> bool:
    if path in {"/api/v1/projects", "/api/v1/companies", "/api/v1/map/projects"}:
        return True
    if path.startswith("/api/v1/projects/") or path.startswith("/api/v1/companies/"):
        return True
    return False

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"

    if _should_log_request_timing(request.url.path) or duration_ms >= settings.request_timing_threshold_ms:
        logger.info(
            "request_timing method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

    return response


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs_url": "/docs",
    }
