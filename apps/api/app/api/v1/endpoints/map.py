from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.public import MapProjectsResponse
from app.services.catalog import ProjectListFilters, get_map_projects

router = APIRouter()


@router.get("/projects", response_model=MapProjectsResponse)
async def get_map_projects_endpoint(
    city: str | None = None,
    company_id: str | None = None,
    project_business_type: str | None = None,
    government_program_type: str | None = None,
    project_urban_renewal_type: str | None = None,
    permit_status: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> MapProjectsResponse:
    filters = ProjectListFilters(
        city=city,
        company_id=UUID(company_id) if company_id else None,
        project_business_type=project_business_type,
        government_program_type=government_program_type,
        project_urban_renewal_type=project_urban_renewal_type,
        permit_status=permit_status,
        page=1,
        page_size=500,
    )
    return MapProjectsResponse.model_validate(await get_map_projects(session, filters))
