from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Pagination, SelectOption


class ValueTrustResponse(BaseModel):
    value_origin_type: str
    confidence_level: str


class CompanyListItem(BaseModel):
    id: UUID
    name_he: str
    ticker: str | None = None
    project_count: int = 0
    city_count: int = 0
    latest_report_period_end: date | None = None
    latest_published_at: date | None = None
    known_unsold_units: int | None = None
    projects_with_precise_location_count: int = 0


class CompaniesListResponse(BaseModel):
    items: list[CompanyListItem] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)


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
    government_program_type: str
    project_urban_renewal_type: str
    project_status: str | None = None
    permit_status: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    latest_snapshot_date: date | None = None
    location_confidence: str
    location_quality: str
    sell_through_rate: Decimal | None = None


class ProjectsListResponse(BaseModel):
    items: list[ProjectListItem] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)


class ProjectIdentity(BaseModel):
    project_id: UUID
    canonical_name: str
    company: ProjectCompanySummary


class ProjectClassification(BaseModel):
    project_business_type: str
    government_program_type: str
    project_urban_renewal_type: str
    project_status: str | None = None
    permit_status: str | None = None
    classification_confidence: str
    trust: dict[str, ValueTrustResponse] = Field(default_factory=dict)


class ProjectLocation(BaseModel):
    city: str | None = None
    neighborhood: str | None = None
    district: str | None = None
    location_confidence: str
    location_quality: str
    trust: dict[str, ValueTrustResponse] = Field(default_factory=dict)


class ProjectSnapshotDetail(BaseModel):
    snapshot_id: UUID
    snapshot_date: date
    project_status: str | None = None
    permit_status: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    trust: dict[str, ValueTrustResponse] = Field(default_factory=dict)


class ProjectDerivedMetrics(BaseModel):
    sell_through_rate: Decimal | None = None
    known_unsold_units: int | None = None
    latest_known_avg_price_per_sqm: Decimal | None = None
    known_margin_signal: str | None = None


class ProjectAddressResponse(BaseModel):
    id: UUID
    address_text_raw: str | None = None
    city: str | None = None
    street: str | None = None
    house_number_from: int | None = None
    house_number_to: int | None = None
    lat: Decimal | None = None
    lng: Decimal | None = None
    location_confidence: str
    location_quality: str
    is_primary: bool
    value_origin_type: str = "unknown"


class SourceQualityResponse(BaseModel):
    source_company: str
    source_report_name: str | None = None
    report_period_end: date
    published_at: date | None = None
    source_url: str
    source_pages: str | None = None
    confidence_level: str
    missing_fields: list[str] = Field(default_factory=list)
    value_origin_summary: dict[str, int] = Field(default_factory=dict)


class FieldProvenanceResponse(BaseModel):
    field_name: str
    raw_value: str | None = None
    normalized_value: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    extraction_method: str
    confidence_score: Decimal | None = None
    value_origin_type: str
    review_status: str
    review_note: str | None = None


class ProjectDetailResponse(BaseModel):
    identity: ProjectIdentity
    classification: ProjectClassification
    location: ProjectLocation
    latest_snapshot: ProjectSnapshotDetail
    derived_metrics: ProjectDerivedMetrics
    addresses: list[ProjectAddressResponse] = Field(default_factory=list)
    source_quality: SourceQualityResponse
    field_provenance: list[FieldProvenanceResponse] = Field(default_factory=list)


class ProjectHistorySnapshot(BaseModel):
    snapshot_id: UUID
    snapshot_date: date
    report_id: UUID
    report_period_end: date | None = None
    project_status: str | None = None
    permit_status: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    sell_through_rate: Decimal | None = None
    sold_units_delta: int | None = None
    unsold_units_delta: int | None = None


class ProjectHistoryResponse(BaseModel):
    project_id: UUID
    snapshots: list[ProjectHistorySnapshot] = Field(default_factory=list)


class CompanyKpiSummary(BaseModel):
    known_unsold_units: int | None = None
    projects_with_precise_location_count: int = 0
    company_city_spread: int = 0
    latest_known_avg_price_per_sqm: Decimal | None = None


class CompanyCitySummary(BaseModel):
    city: str
    project_count: int


class CompanyBusinessTypeSummary(BaseModel):
    project_business_type: str
    project_count: int


class CompanyProjectListItem(BaseModel):
    id: UUID
    canonical_name: str
    city: str | None = None
    project_business_type: str
    project_status: str | None = None
    permit_status: str | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    latest_snapshot_date: date | None = None
    location_quality: str


class CompanyDetailResponse(BaseModel):
    id: UUID
    name_he: str
    ticker: str | None = None
    latest_report_name: str | None = None
    latest_report_period_end: date | None = None
    latest_published_at: date | None = None
    project_count: int
    city_count: int
    kpis: CompanyKpiSummary
    city_coverage: list[CompanyCitySummary] = Field(default_factory=list)
    project_business_type_distribution: list[CompanyBusinessTypeSummary] = Field(default_factory=list)
    projects: list[CompanyProjectListItem] = Field(default_factory=list)


class CompanyProjectsResponse(BaseModel):
    company_id: UUID
    items: list[CompanyProjectListItem] = Field(default_factory=list)


class FiltersMetadataResponse(BaseModel):
    companies: list[SelectOption] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    project_business_types: list[str] = Field(default_factory=list)
    government_program_types: list[str] = Field(default_factory=list)
    project_urban_renewal_types: list[str] = Field(default_factory=list)
    permit_statuses: list[str] = Field(default_factory=list)


class MapProjectProperties(BaseModel):
    project_id: UUID
    canonical_name: str
    company_name: str
    city: str | None = None
    project_business_type: str
    project_status: str | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    unsold_units: int | None = None
    location_confidence: str
    location_quality: str


class GeoJsonFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any] | None = None
    properties: MapProjectProperties


class MapProjectsResponse(BaseModel):
    features: list[GeoJsonFeature] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
