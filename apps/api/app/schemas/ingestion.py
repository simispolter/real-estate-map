from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AdminReportSummary(BaseModel):
    id: UUID
    company_id: UUID
    company_name_he: str
    report_name: str | None = None
    report_type: str
    period_type: str
    period_end_date: date
    published_at: date | None = None
    source_url: str | None = None
    source_file_path: str | None = None
    source_is_official: bool
    source_label: str | None = None
    ingestion_status: str
    notes: str | None = None
    candidate_count: int = 0
    created_at: datetime
    updated_at: datetime


class AdminReportsListResponse(BaseModel):
    items: list[AdminReportSummary] = Field(default_factory=list)


class AdminParserRunItem(BaseModel):
    id: UUID
    report_id: UUID
    staging_report_id: UUID | None = None
    status: str
    parser_version: str
    source_label: str | None = None
    source_reference: str | None = None
    source_checksum: str | None = None
    sections_found: int = 0
    candidate_count: int = 0
    field_candidate_count: int = 0
    address_candidate_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminParserRunsResponse(BaseModel):
    report_id: UUID
    items: list[AdminParserRunItem] = Field(default_factory=list)


class AdminQaDistributionItem(BaseModel):
    key: str
    count: int


class AdminQaMissingFieldItem(BaseModel):
    field_name: str
    missing_count: int


class AdminQaFamilyCoverageItem(BaseModel):
    section_kind: str
    section_count: int = 0
    candidate_count: int = 0
    matched_existing_count: int = 0
    new_project_count: int = 0
    ambiguous_count: int = 0
    ignored_count: int = 0


class AdminReportQaSummary(BaseModel):
    total_candidates: int = 0
    projects_detected: int = 0
    matched_existing_projects: int = 0
    new_projects_needed: int = 0
    ambiguous_candidates: int = 0
    rejected_or_ignored_candidates: int = 0
    published_candidates: int = 0
    missing_key_field_total: int = 0
    latest_parser_sections_found: int = 0
    latest_parser_candidate_count: int = 0


class AdminReportQaResponse(BaseModel):
    report_id: UUID
    summary: AdminReportQaSummary
    lifecycle_stage_distribution: list[AdminQaDistributionItem] = Field(default_factory=list)
    disclosure_level_distribution: list[AdminQaDistributionItem] = Field(default_factory=list)
    family_coverage: list[AdminQaFamilyCoverageItem] = Field(default_factory=list)
    missing_key_fields: list[AdminQaMissingFieldItem] = Field(default_factory=list)
    latest_parser_run: AdminParserRunItem | None = None


class AdminFieldCandidateInput(BaseModel):
    id: UUID | None = None
    field_name: str
    raw_value: str | None = None
    normalized_value: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    source_table_name: str | None = None
    source_row_label: str | None = None
    extraction_profile_key: str | None = None
    value_origin_type: str = "manual"
    confidence_level: str = "medium"
    review_status: str = "pending"
    review_notes: str | None = None


class AdminAddressCandidateInput(BaseModel):
    id: UUID | None = None
    address_text_raw: str | None = None
    street: str | None = None
    house_number_from: int | None = None
    house_number_to: int | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    location_confidence: str = "unknown"
    is_primary: bool = False
    value_origin_type: str = "manual"
    confidence_level: str = "medium"
    review_status: str = "pending"
    review_notes: str | None = None


class AdminCandidateSummary(BaseModel):
    id: UUID
    candidate_project_name: str
    city: str | None = None
    neighborhood: str | None = None
    candidate_lifecycle_stage: str | None = None
    candidate_disclosure_level: str | None = None
    candidate_section_kind: str | None = None
    matching_status: str
    publish_status: str
    confidence_level: str
    review_status: str
    matched_project_id: UUID | None = None
    matched_project_name: str | None = None
    review_notes: str | None = None
    diff_summary: dict[str, Any] | None = None


class AdminReportDetailResponse(AdminReportSummary):
    staging_report_id: UUID
    staging_publish_status: str
    staging_review_status: str
    staging_notes_internal: str | None = None
    candidates: list[AdminCandidateSummary] = Field(default_factory=list)


class AdminReportCreateRequest(BaseModel):
    company_id: UUID
    report_name: str
    report_type: str
    period_type: str
    period_end_date: date
    published_at: date | None = None
    source_url: str | None = None
    source_file_path: str | None = None
    source_is_official: bool = False
    source_label: str | None = None
    ingestion_status: str = "draft"
    notes: str | None = None


class AdminReportUpdateRequest(BaseModel):
    report_name: str | None = None
    report_type: str | None = None
    period_type: str | None = None
    period_end_date: date | None = None
    published_at: date | None = None
    source_url: str | None = None
    source_file_path: str | None = None
    source_is_official: bool | None = None
    source_label: str | None = None
    ingestion_status: str | None = None
    notes: str | None = None
    staging_publish_status: str | None = None
    staging_review_status: str | None = None
    staging_notes_internal: str | None = None


class AdminCandidateCreateRequest(BaseModel):
    candidate_project_name: str
    city: str | None = None
    neighborhood: str | None = None
    candidate_lifecycle_stage: str | None = None
    candidate_disclosure_level: str | None = None
    candidate_section_kind: str | None = None
    candidate_materiality_flag: bool | None = None
    source_table_name: str | None = None
    source_row_label: str | None = None
    extraction_profile_key: str | None = None
    project_business_type: str | None = None
    government_program_type: str = "none"
    project_urban_renewal_type: str = "none"
    project_status: str | None = None
    permit_status: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    location_confidence: str = "unknown"
    value_origin_type: str = "manual"
    confidence_level: str = "medium"
    review_status: str = "pending"
    review_notes: str | None = None
    staging_section_id: UUID | None = None
    field_candidates: list[AdminFieldCandidateInput] = Field(default_factory=list)
    address_candidates: list[AdminAddressCandidateInput] = Field(default_factory=list)


class AdminCandidateUpdateRequest(BaseModel):
    candidate_project_name: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    candidate_lifecycle_stage: str | None = None
    candidate_disclosure_level: str | None = None
    candidate_section_kind: str | None = None
    candidate_materiality_flag: bool | None = None
    source_table_name: str | None = None
    source_row_label: str | None = None
    extraction_profile_key: str | None = None
    project_business_type: str | None = None
    government_program_type: str | None = None
    project_urban_renewal_type: str | None = None
    project_status: str | None = None
    permit_status: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    location_confidence: str | None = None
    value_origin_type: str | None = None
    confidence_level: str | None = None
    matching_status: str | None = None
    publish_status: str | None = None
    review_status: str | None = None
    review_notes: str | None = None
    matched_project_id: UUID | None = None
    field_candidates: list[AdminFieldCandidateInput] | None = None
    address_candidates: list[AdminAddressCandidateInput] | None = None


class MatchSuggestionResponse(BaseModel):
    project_id: UUID
    canonical_name: str
    city: str | None = None
    neighborhood: str | None = None
    similarity_score: float
    match_state: str = "no_match"
    reasons_json: dict[str, Any] = Field(default_factory=dict)


class CandidateCompareRowResponse(BaseModel):
    field_name: str
    canonical_value: str | None = None
    staging_value: str | None = None
    raw_source_value: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    value_origin_type: str
    confidence_level: str
    changed: bool


class CandidateDiffItemResponse(BaseModel):
    field_name: str
    previous_value: str | None = None
    incoming_value: str | None = None
    changed: bool


class AdminFieldCandidateResponse(AdminFieldCandidateInput):
    id: UUID
    created_at: datetime
    updated_at: datetime


class AdminAddressCandidateResponse(AdminAddressCandidateInput):
    id: UUID
    created_at: datetime
    updated_at: datetime


class AdminCandidateDetailResponse(BaseModel):
    id: UUID
    staging_report_id: UUID
    report_id: UUID
    company_id: UUID
    company_name_he: str
    candidate_project_name: str
    city: str | None = None
    neighborhood: str | None = None
    candidate_lifecycle_stage: str | None = None
    candidate_disclosure_level: str | None = None
    candidate_section_kind: str | None = None
    candidate_materiality_flag: bool | None = None
    source_table_name: str | None = None
    source_row_label: str | None = None
    extraction_profile_key: str | None = None
    project_business_type: str | None = None
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
    location_confidence: str
    value_origin_type: str
    confidence_level: str
    matching_status: str
    publish_status: str
    review_status: str
    review_notes: str | None = None
    matched_project_id: UUID | None = None
    matched_project_name: str | None = None
    field_candidates: list[AdminFieldCandidateResponse] = Field(default_factory=list)
    address_candidates: list[AdminAddressCandidateResponse] = Field(default_factory=list)
    match_suggestions: list[MatchSuggestionResponse] = Field(default_factory=list)
    compare_rows: list[CandidateCompareRowResponse] = Field(default_factory=list)
    diff_summary: list[CandidateDiffItemResponse] = Field(default_factory=list)
    extension_blocks: dict[str, dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AdminReportCandidatesResponse(BaseModel):
    report_id: UUID
    items: list[AdminCandidateSummary] = Field(default_factory=list)


class AdminCandidateMatchRequest(BaseModel):
    match_status: str
    matched_project_id: UUID | None = None
    reviewer_note: str | None = None


class AdminCandidatePublishRequest(BaseModel):
    reviewer_note: str | None = None
