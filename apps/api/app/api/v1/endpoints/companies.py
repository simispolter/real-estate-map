from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.public import CompaniesListResponse, CompanyDetailResponse, CompanyProjectsResponse
from app.services.catalog import CompanyListFilters, get_company_detail, get_company_projects, list_companies

router = APIRouter()


@router.get("", response_model=CompaniesListResponse)
async def list_companies_endpoint(
    q: str | None = Query(default=None),
    city: str | None = Query(default=None),
    sort_by: str = Query(default="project_count"),
    session: AsyncSession = Depends(get_db_session),
) -> CompaniesListResponse:
    items = await list_companies(session, CompanyListFilters(q=q, city=city, sort_by=sort_by))
    return CompaniesListResponse(
        items=items,
        pagination={"page": 1, "page_size": len(items) or 1, "total": len(items)},
    )


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> CompanyDetailResponse:
    company = await get_company_detail(session, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyDetailResponse.model_validate(company)


@router.get("/{company_id}/projects", response_model=CompanyProjectsResponse)
async def get_company_projects_endpoint(
    company_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> CompanyProjectsResponse:
    items = await get_company_projects(session, company_id)
    return CompanyProjectsResponse(company_id=company_id, items=items)
