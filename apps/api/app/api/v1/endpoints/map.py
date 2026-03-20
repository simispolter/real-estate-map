from fastapi import APIRouter

from app.schemas.public import MapProjectsResponse

router = APIRouter()


@router.get("/projects", response_model=MapProjectsResponse)
async def get_map_projects() -> MapProjectsResponse:
    return MapProjectsResponse(
        features=[],
        meta={"message": "Mapbox integration is intentionally deferred to a later phase."},
    )
