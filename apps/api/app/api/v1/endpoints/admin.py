from fastapi import APIRouter

from app.schemas.admin import AdminOverviewResponse

router = APIRouter()


@router.get("/overview", response_model=AdminOverviewResponse)
async def get_admin_overview() -> AdminOverviewResponse:
    return AdminOverviewResponse(
        pending_reports=0,
        pending_reviews=0,
        pending_location_assignments=0,
        pending_publish_candidates=0,
    )
