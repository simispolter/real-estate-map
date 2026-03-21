from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.admin import (
    AdminAddressUpsertRequest,
    AdminOverviewResponse,
    AdminProjectDetailResponse,
    AdminProjectsListResponse,
    AdminProjectUpdateRequest,
)
from app.services.admin_review import (
    delete_project_address,
    get_admin_project_detail,
    list_admin_projects,
    update_admin_project,
    upsert_project_address,
)

router = APIRouter()


@router.get("/overview", response_model=AdminOverviewResponse)
async def get_admin_overview() -> AdminOverviewResponse:
    return AdminOverviewResponse(
        pending_reports=0,
        pending_reviews=0,
        pending_location_assignments=0,
        pending_publish_candidates=0,
    )


@router.get("/projects", response_model=AdminProjectsListResponse)
async def get_admin_projects(
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectsListResponse:
    return AdminProjectsListResponse(items=await list_admin_projects(session))


@router.get("/projects/{project_id}", response_model=AdminProjectDetailResponse)
async def get_admin_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await get_admin_project_detail(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.patch("/projects/{project_id}", response_model=AdminProjectDetailResponse)
async def patch_admin_project(
    project_id: UUID,
    payload: AdminProjectUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await update_admin_project(session, project_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.post("/projects/{project_id}/addresses", response_model=AdminProjectDetailResponse)
async def create_admin_project_address(
    project_id: UUID,
    payload: AdminAddressUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await upsert_project_address(session, project_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.put("/projects/{project_id}/addresses/{address_id}", response_model=AdminProjectDetailResponse)
async def update_admin_project_address(
    project_id: UUID,
    address_id: UUID,
    payload: AdminAddressUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await upsert_project_address(session, project_id, payload.model_dump(exclude_unset=True), address_id=address_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project or address not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.delete("/projects/{project_id}/addresses/{address_id}", response_model=AdminProjectDetailResponse)
async def remove_admin_project_address(
    project_id: UUID,
    address_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await delete_project_address(session, project_id, address_id, reason="Deleted from admin review")
    if project is None:
        raise HTTPException(status_code=404, detail="Project or address not found")
    return AdminProjectDetailResponse.model_validate(project)
