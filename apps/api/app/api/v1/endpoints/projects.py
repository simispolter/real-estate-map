from uuid import UUID

from fastapi import APIRouter

from app.schemas.public import (
    ProjectDetailResponse,
    ProjectHistoryResponse,
    ProjectsListResponse,
)

router = APIRouter()


@router.get("", response_model=ProjectsListResponse)
async def list_projects() -> ProjectsListResponse:
    return ProjectsListResponse(items=[])


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: UUID) -> ProjectDetailResponse:
    return ProjectDetailResponse(
        project_id=project_id,
        message="Project detail endpoint scaffolded for Sprint 2.",
    )


@router.get("/{project_id}/history", response_model=ProjectHistoryResponse)
async def get_project_history(project_id: UUID) -> ProjectHistoryResponse:
    return ProjectHistoryResponse(project_id=project_id, snapshots=[])
