from uuid import UUID

from fastapi import APIRouter

from app.schemas.public import CompaniesListResponse, CompanyDetailResponse

router = APIRouter()


@router.get("", response_model=CompaniesListResponse)
async def list_companies() -> CompaniesListResponse:
    return CompaniesListResponse(items=[])


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(company_id: UUID) -> CompanyDetailResponse:
    return CompanyDetailResponse(
        company_id=company_id,
        message="Company detail endpoint scaffolded for Sprint 2.",
    )
