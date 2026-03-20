from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.app_env,
        "version": settings.app_version,
    }
