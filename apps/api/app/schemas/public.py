from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Pagination


class CompanyListItem(BaseModel):
    id: UUID
    name_he: str
    ticker: str | None = None


class CompaniesListResponse(BaseModel):
    items: list[CompanyListItem] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)


class CompanyDetailResponse(BaseModel):
    company_id: UUID
    message: str


class ProjectCompanySummary(BaseModel):
    id: UUID
    name_he: str


class ProjectListItem(BaseModel):
    project_id: UUID
    canonical_name: str
    company: ProjectCompanySummary
    city: str | None = None
    neighborhood: str | None = None
    project_business_type: str
    project_status: str | None = None
    permit_status: str | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: float | None = None
    gross_margin_expected_pct: float | None = None
    latest_snapshot_date: str | None = None
    location_confidence: str


class ProjectsListResponse(BaseModel):
    items: list[ProjectListItem] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)


class ProjectDetailResponse(BaseModel):
    project_id: UUID
    message: str


class ProjectHistorySnapshot(BaseModel):
    snapshot_id: UUID
    snapshot_date: str
    report_id: UUID
    project_status: str | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    avg_price_per_sqm_cumulative: float | None = None
    gross_profit_unrecognized: float | None = None


class ProjectHistoryResponse(BaseModel):
    project_id: UUID
    snapshots: list[ProjectHistorySnapshot] = Field(default_factory=list)


class GeoJsonFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class MapProjectsResponse(BaseModel):
    features: list[GeoJsonFeature] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
