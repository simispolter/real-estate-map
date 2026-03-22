from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.public import (
    ProjectDetailResponse,
    ProjectHistoryResponse,
    ProjectsListResponse,
)
from app.services.catalog import (
    ProjectListFilters,
    export_projects_csv,
    get_project_detail,
    get_project_history,
    list_projects,
)

router = APIRouter()


def _filters_from_query(
    q: str | None,
    city: str | None,
    company_id: UUID | None,
    project_business_type: str | None,
    government_program_type: str | None,
    project_urban_renewal_type: str | None,
    permit_status: str | None,
    location_confidence: str | None,
    page: int,
    page_size: int,
) -> ProjectListFilters:
    return ProjectListFilters(
        q=q,
        city=city,
        company_id=company_id,
        project_business_type=project_business_type,
        government_program_type=government_program_type,
        project_urban_renewal_type=project_urban_renewal_type,
        permit_status=permit_status,
        location_confidence=location_confidence,
        page=page,
        page_size=page_size,
    )


@router.get("/export.csv")
async def export_projects_csv_endpoint(
    q: str | None = Query(default=None),
    city: str | None = Query(default=None),
    company_id: UUID | None = Query(default=None),
    project_business_type: str | None = Query(default=None),
    government_program_type: str | None = Query(default=None),
    project_urban_renewal_type: str | None = Query(default=None),
    permit_status: str | None = Query(default=None),
    location_confidence: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    csv_content = await export_projects_csv(
        session,
        _filters_from_query(
            q,
            city,
            company_id,
            project_business_type,
            government_program_type,
            project_urban_renewal_type,
            permit_status,
            location_confidence,
            1,
            1000,
        ),
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="projects-export.csv"'},
    )


@router.get("", response_model=ProjectsListResponse)
async def list_projects_endpoint(
    q: str | None = Query(default=None),
    city: str | None = Query(default=None),
    company_id: UUID | None = Query(default=None),
    project_business_type: str | None = Query(default=None),
    government_program_type: str | None = Query(default=None),
    project_urban_renewal_type: str | None = Query(default=None),
    permit_status: str | None = Query(default=None),
    location_confidence: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectsListResponse:
    items, total = await list_projects(
        session,
        _filters_from_query(
            q,
            city,
            company_id,
            project_business_type,
            government_program_type,
            project_urban_renewal_type,
            permit_status,
            location_confidence,
            page,
            page_size,
        ),
    )
    return ProjectsListResponse(
        items=items,
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectDetailResponse:
    project = await get_project_detail(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDetailResponse.model_validate(project)


@router.get("/{project_id}/history", response_model=ProjectHistoryResponse)
async def get_project_history_endpoint(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ProjectHistoryResponse:
    return ProjectHistoryResponse(project_id=project_id, snapshots=await get_project_history(session, project_id))
