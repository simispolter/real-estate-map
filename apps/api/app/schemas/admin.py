from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.public import (
    FieldProvenanceResponse,
    ProjectAddressResponse,
    ProjectClassification,
    ProjectCompanySummary,
    ProjectDisplayGeometryResponse,
    ProjectLocation,
    ProjectSnapshotDetail,
)


class AdminOverviewResponse(BaseModel):
    pending_reports: int = Field(default=0, ge=0)
    pending_reviews: int = Field(default=0, ge=0)
    pending_location_assignments: int = Field(default=0, ge=0)
    pending_publish_candidates: int = Field(default=0, ge=0)


class AdminAuditLogItem(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None = None
    diff_json: dict | None = None
    comment: str | None = None
    created_at: datetime


class AdminProjectAliasItem(BaseModel):
    id: UUID
    alias_name: str
    value_origin_type: str
    alias_source_type: str = "manual"
    source_report_id: UUID | None = None
    is_active: bool = True
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminProjectSourceItem(BaseModel):
    report_id: UUID
    report_name: str | None = None
    source_label: str | None = None
    source_url: str | None = None
    ingestion_status: str
    period_end_date: date
    published_at: date | None = None


class AdminProjectLinkedCandidateItem(BaseModel):
    candidate_id: UUID
    candidate_project_name: str
    matching_status: str
    publish_status: str
    review_status: str
    source_report_id: UUID
    source_report_name: str | None = None


class AdminSnapshotSummary(BaseModel):
    id: UUID
    report_id: UUID
    report_name: str | None = None
    snapshot_date: date
    lifecycle_stage: str | None = None
    disclosure_level: str | None = None
    source_section_kind: str | None = None
    project_status: str | None = None
    permit_status: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    chronology_status: str = "ok"
    chronology_notes: str | None = None
    notes_internal: str | None = None
    diff_summary: dict[str, dict[str, str | bool | None]] = Field(default_factory=dict)
    data_families: list[str] = Field(default_factory=list)
    extension_blocks: dict[str, dict[str, object | None]] = Field(default_factory=dict)


class AdminProjectListItem(BaseModel):
    id: UUID
    canonical_name: str
    company: ProjectCompanySummary
    city: str | None = None
    lifecycle_stage: str | None = None
    disclosure_level: str | None = None
    project_business_type: str
    government_program_type: str
    project_urban_renewal_type: str
    project_status: str | None = None
    permit_status: str | None = None
    classification_confidence: str
    location_confidence: str
    needs_admin_review: bool
    latest_snapshot_date: date | None = None
    source_count: int = 0
    address_count: int = 0
    is_publicly_visible: bool
    source_conflict_flag: bool


class AdminProjectsListResponse(BaseModel):
    items: list[AdminProjectListItem] = Field(default_factory=list)


class AdminProjectDetailResponse(BaseModel):
    id: UUID
    canonical_name: str
    company: ProjectCompanySummary
    classification: ProjectClassification
    location: ProjectLocation
    display_geometry: ProjectDisplayGeometryResponse
    latest_snapshot: ProjectSnapshotDetail | None = None
    addresses: list[ProjectAddressResponse] = Field(default_factory=list)
    aliases: list[AdminProjectAliasItem] = Field(default_factory=list)
    snapshots: list[AdminSnapshotSummary] = Field(default_factory=list)
    linked_sources: list[AdminProjectSourceItem] = Field(default_factory=list)
    linked_candidates: list[AdminProjectLinkedCandidateItem] = Field(default_factory=list)
    field_provenance: list[FieldProvenanceResponse] = Field(default_factory=list)
    provenance_summary: dict[str, int] = Field(default_factory=dict)
    is_publicly_visible: bool = False
    source_conflict_flag: bool = False
    notes_internal: str | None = None
    audit_log: list[AdminAuditLogItem] = Field(default_factory=list)


class AdminProjectCreateRequest(BaseModel):
    canonical_name: str
    company_id: UUID
    city: str | None = None
    neighborhood: str | None = None
    lifecycle_stage: str | None = None
    disclosure_level: str | None = None
    project_business_type: str
    government_program_type: str = "none"
    project_urban_renewal_type: str = "none"
    location_confidence: str = "city_only"
    is_publicly_visible: bool = False
    source_conflict_flag: bool = False
    notes_internal: str | None = None
    value_origin_type: str = "manual"
    reviewer_note: str | None = None


class AdminProjectUpdateRequest(BaseModel):
    canonical_name: str | None = None
    company_id: UUID | None = None
    lifecycle_stage: str | None = None
    disclosure_level: str | None = None
    project_business_type: str | None = None
    government_program_type: str | None = None
    project_urban_renewal_type: str | None = None
    permit_status: str | None = None
    project_status: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    location_confidence: str | None = None
    is_publicly_visible: bool | None = None
    source_conflict_flag: bool | None = None
    notes_internal: str | None = None
    field_origin_types: dict[str, str] = Field(default_factory=dict)
    change_reason: str | None = None


class AdminProjectAliasCreateRequest(BaseModel):
    alias_name: str
    value_origin_type: str = "manual"
    alias_source_type: str = "manual"
    source_report_id: UUID | None = None
    is_active: bool = True
    notes: str | None = None
    make_preferred: bool = False
    reviewer_note: str | None = None


class AdminAddressUpsertRequest(BaseModel):
    address_text_raw: str | None = None
    street: str | None = None
    house_number_from: int | None = None
    house_number_to: int | None = None
    city: str | None = None
    parcel_block: str | None = None
    parcel_number: str | None = None
    sub_parcel: str | None = None
    address_note: str | None = None
    lat: float | None = None
    lng: float | None = None
    location_confidence: str = "city_only"
    is_primary: bool = False
    normalized_display_address: str | None = None
    geocoding_method: str | None = None
    geocoding_source_label: str | None = None
    value_origin_type: str = "reported"
    change_reason: str | None = None


class AdminLocationReferenceResponse(BaseModel):
    cities: list[str] = Field(default_factory=list)
    streets: list[str] = Field(default_factory=list)


class AdminProjectDisplayGeometryUpdateRequest(BaseModel):
    geometry_type: str
    geometry_source: str = "manual_override"
    location_confidence: str
    geometry_geojson: dict | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    address_summary: str | None = None
    note: str | None = None
    change_reason: str | None = None


class AdminSnapshotCreateRequest(BaseModel):
    report_id: UUID | None = None
    snapshot_date: date
    lifecycle_stage: str | None = None
    disclosure_level: str | None = None
    source_section_kind: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    permit_status: str | None = None
    project_status: str | None = None
    notes_internal: str | None = None
    value_origin_type: str = "manual"
    confidence_level: str = "medium"
    reviewer_note: str | None = None


class AdminSnapshotUpdateRequest(BaseModel):
    report_id: UUID | None = None
    snapshot_date: date | None = None
    lifecycle_stage: str | None = None
    disclosure_level: str | None = None
    source_section_kind: str | None = None
    total_units: int | None = None
    marketed_units: int | None = None
    sold_units_cumulative: int | None = None
    unsold_units: int | None = None
    avg_price_per_sqm_cumulative: Decimal | None = None
    gross_profit_total_expected: Decimal | None = None
    gross_margin_expected_pct: Decimal | None = None
    permit_status: str | None = None
    project_status: str | None = None
    notes_internal: str | None = None
    value_origin_type: str = "manual"
    confidence_level: str = "medium"
    reviewer_note: str | None = None


class AdminProjectSnapshotsResponse(BaseModel):
    project_id: UUID
    items: list[AdminSnapshotSummary] = Field(default_factory=list)


class AdminIntakeListItem(BaseModel):
    id: UUID
    candidate_project_name: str
    company: ProjectCompanySummary
    city: str | None = None
    source_report_id: UUID
    source_report_name: str | None = None
    matching_status: str
    confidence_level: str
    review_status: str
    publish_status: str
    matched_project_id: UUID | None = None
    matched_project_name: str | None = None


class AdminIntakeListResponse(BaseModel):
    items: list[AdminIntakeListItem] = Field(default_factory=list)


class AdminDuplicateSuggestionItem(BaseModel):
    id: UUID
    project_id: UUID
    project_name: str
    duplicate_project_id: UUID
    duplicate_project_name: str
    company_name: str
    city: str | None = None
    duplicate_city: str | None = None
    match_state: str
    score: Decimal
    reasons_json: dict[str, object] = Field(default_factory=dict)
    review_status: str


class AdminDuplicatesResponse(BaseModel):
    items: list[AdminDuplicateSuggestionItem] = Field(default_factory=list)


class AdminMergeProjectsRequest(BaseModel):
    winner_project_id: UUID
    loser_project_id: UUID
    merge_reason: str


class AdminCoverageCompanyItem(BaseModel):
    company_id: UUID
    company_name_he: str
    is_active: bool = True
    is_in_scope: bool
    out_of_scope_reason: str | None = None
    coverage_priority: str
    latest_report_registered_id: UUID | None = None
    latest_report_registered_name: str | None = None
    latest_report_published: date | None = None
    latest_report_ingested_id: UUID | None = None
    latest_report_ingested_name: str | None = None
    historical_coverage_start: date | None = None
    historical_coverage_end: date | None = None
    historical_coverage_status: str
    backfill_status: str = "not_started"
    reports_registered: int = 0
    reports_published_into_canonical: int = 0
    projects_created: int = 0
    snapshots_created: int = 0
    projects_missing_key_fields: int = 0
    projects_city_only_location: int = 0
    projects_with_exact_or_approximate_geometry: int = 0
    notes: str | None = None


class AdminFieldCompletenessItem(BaseModel):
    field_name: str
    complete_count: int = 0
    missing_count: int = 0


class AdminCoverageSummary(BaseModel):
    companies_in_scope: int = 0
    companies_with_latest_report_ingested: int = 0
    companies_missing_latest_report: int = 0
    reports_registered: int = 0
    reports_published_into_canonical: int = 0
    projects_created: int = 0
    snapshots_created: int = 0
    unmatched_candidates: int = 0
    ambiguous_candidates: int = 0
    projects_missing_key_fields: int = 0
    projects_city_only_location: int = 0
    projects_with_exact_or_approximate_geometry: int = 0


class AdminCoverageDashboardResponse(BaseModel):
    summary: AdminCoverageSummary
    field_completeness: list[AdminFieldCompletenessItem] = Field(default_factory=list)
    companies: list[AdminCoverageCompanyItem] = Field(default_factory=list)


class AdminCoverageUpdateRequest(BaseModel):
    is_active: bool | None = None
    is_in_scope: bool | None = None
    out_of_scope_reason: str | None = None
    coverage_priority: str | None = None
    latest_report_registered_id: UUID | None = None
    latest_report_ingested_id: UUID | None = None
    latest_report_published_date: date | None = None
    historical_coverage_start: date | None = None
    historical_coverage_end: date | None = None
    historical_coverage_status: str | None = None
    backfill_status: str | None = None
    notes: str | None = None
    change_reason: str | None = None


class AdminCoverageReportItem(BaseModel):
    report_id: UUID
    company_id: UUID
    company_name_he: str
    report_name: str | None = None
    report_type: str
    period_type: str
    period_end_date: date
    published_at: date | None = None
    is_in_scope: bool = True
    source_is_official: bool = False
    source_label: str | None = None
    source_url: str | None = None
    ingestion_status: str
    linked_project_count: int = 0
    linked_snapshot_count: int = 0
    is_published_into_canonical: bool = False
    is_latest_registered: bool = False
    is_latest_ingested: bool = False


class AdminCoverageReportsResponse(BaseModel):
    items: list[AdminCoverageReportItem] = Field(default_factory=list)


class AdminCoverageGapSummary(BaseModel):
    total_items: int = 0
    missing_location: int = 0
    missing_metrics: int = 0
    stale_or_missing_snapshot: int = 0


class AdminCoverageGapItem(BaseModel):
    project_id: UUID
    project_name: str
    company_id: UUID
    company_name_he: str
    city: str | None = None
    location_confidence: str
    location_quality: str
    latest_snapshot_date: date | None = None
    latest_snapshot_age_days: int | None = None
    missing_fields: list[str] = Field(default_factory=list)
    source_count: int = 0
    address_count: int = 0
    is_publicly_visible: bool = False
    backfill_status: str = "not_started"


class AdminCoverageGapsResponse(BaseModel):
    summary: AdminCoverageGapSummary
    items: list[AdminCoverageGapItem] = Field(default_factory=list)


class AdminCoverageBulkRequest(BaseModel):
    target_type: str
    action: str
    ids: list[UUID] = Field(default_factory=list)
    is_in_scope: bool | None = None
    backfill_status: str | None = None
    note: str | None = None


class AdminCoverageBulkResponse(BaseModel):
    applied_count: int = 0
    target_type: str
    action: str


class AdminLocationReviewSummary(BaseModel):
    total_items: int = 0
    city_only: int = 0
    unknown: int = 0
    manual_geometry: int = 0
    geocoding_ready: int = 0


class AdminLocationReviewItem(BaseModel):
    project_id: UUID
    project_name: str
    company: ProjectCompanySummary
    city: str | None = None
    neighborhood: str | None = None
    location_confidence: str
    location_quality: str
    geometry_type: str
    geometry_source: str
    geometry_is_manual: bool = False
    address_count: int = 0
    primary_address_id: UUID | None = None
    primary_address_summary: str | None = None
    geocoding_status: str | None = None
    geocoding_method: str | None = None
    geocoding_source_label: str | None = None
    is_geocoding_ready: bool = False
    latest_snapshot_date: date | None = None
    latest_snapshot_age_days: int | None = None
    backfill_status: str = "not_started"
    missing_location_fields: list[str] = Field(default_factory=list)


class AdminLocationReviewResponse(BaseModel):
    summary: AdminLocationReviewSummary
    items: list[AdminLocationReviewItem] = Field(default_factory=list)


class AdminAnomalyItem(BaseModel):
    id: str
    anomaly_type: str
    severity: str
    project_id: UUID
    project_name: str
    company_name: str
    snapshot_id: UUID | None = None
    report_id: UUID | None = None
    source_report_name: str | None = None
    summary: str
    details_json: dict[str, object | None] = Field(default_factory=dict)


class AdminAnomaliesResponse(BaseModel):
    items: list[AdminAnomalyItem] = Field(default_factory=list)


class AdminParserHealthRecentRun(BaseModel):
    id: UUID
    report_id: UUID
    status: str
    candidate_count: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    finished_at: datetime | None = None


class AdminOpsSummary(BaseModel):
    reports_registered: int = 0
    projects_created: int = 0
    snapshots_created: int = 0
    open_anomalies: int = 0
    parser_failed_runs: int = 0
    ready_to_publish: int = 0


class AdminOpsDashboardResponse(BaseModel):
    summary: AdminOpsSummary
    ingestion_health: dict[str, object] = Field(default_factory=dict)
    matching_backlog: dict[str, int] = Field(default_factory=dict)
    publish_backlog: dict[str, int] = Field(default_factory=dict)
    coverage_completeness: dict[str, int] = Field(default_factory=dict)
    location_completeness: dict[str, object] = Field(default_factory=dict)
    parser_health: dict[str, object] = Field(default_factory=dict)
    top_anomalies: list[AdminAnomalyItem] = Field(default_factory=list)


class AdminExternalLayerListItem(BaseModel):
    id: UUID
    layer_name: str
    source_name: str
    source_url: str | None = None
    geometry_type: str
    update_cadence: str
    quality_score: Decimal | None = None
    visibility: str
    notes: str | None = None
    is_active: bool = True
    default_on_map: bool = False
    record_count: int = 0
    relation_count: int = 0
    updated_at: datetime


class AdminExternalLayerRecordItem(BaseModel):
    id: UUID
    external_record_id: str
    label: str | None = None
    city: str | None = None
    effective_date: date | None = None
    properties_json: dict = Field(default_factory=dict)
    update_metadata: dict | None = None
    relation_count: int = 0


class AdminExternalLayerDetailResponse(AdminExternalLayerListItem):
    records: list[AdminExternalLayerRecordItem] = Field(default_factory=list)
    relation_method_breakdown: dict[str, int] = Field(default_factory=dict)


class AdminExternalLayersResponse(BaseModel):
    items: list[AdminExternalLayerListItem] = Field(default_factory=list)


class AdminExternalLayerCreateRequest(BaseModel):
    layer_name: str
    source_name: str
    source_url: str | None = None
    geometry_type: str = "point"
    update_cadence: str = "ad_hoc"
    quality_score: Decimal | None = None
    visibility: str = "public"
    notes: str | None = None
    is_active: bool = True
    default_on_map: bool = False


class AdminExternalLayerUpdateRequest(BaseModel):
    layer_name: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    geometry_type: str | None = None
    update_cadence: str | None = None
    quality_score: Decimal | None = None
    visibility: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    default_on_map: bool | None = None
