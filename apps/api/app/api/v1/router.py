from fastapi import APIRouter

from app.api.v1.endpoints import admin, companies, map, projects

router = APIRouter()
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(companies.router, prefix="/companies", tags=["companies"])
router.include_router(map.router, prefix="/map", tags=["map"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
