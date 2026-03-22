from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


def pg_enum(name: str, *values: str) -> PGEnum:
    return PGEnum(*values, name=name, create_type=False, validate_strings=True)


company_public_status_enum = pg_enum(
    "company_public_status_enum",
    "public",
    "delisted",
    "merged",
)
company_sector_enum = pg_enum("company_sector_enum", "residential_developer")
report_type_enum = pg_enum("report_type_enum", "annual", "q1", "q2", "q3", "prospectus", "presentation")
report_period_type_enum = pg_enum("report_period_type_enum", "annual", "quarterly", "interim")
report_status_enum = pg_enum("report_status_enum", "uploaded", "parsed", "reviewed", "published", "failed")
report_ingestion_status_enum = pg_enum(
    "report_ingestion_status_enum",
    "draft",
    "ready_for_staging",
    "in_review",
    "published",
    "rejected",
)
asset_domain_enum = pg_enum("asset_domain_enum", "residential_only")
project_business_type_enum = pg_enum("project_business_type_enum", "regular_dev", "govt_program", "urban_renewal")
government_program_type_enum = pg_enum(
    "government_program_type_enum",
    "none",
    "mechir_lamishtaken",
    "mechir_metara",
    "dira_bahanaa",
    "other",
)
project_urban_renewal_type_enum = pg_enum(
    "project_urban_renewal_type_enum",
    "none",
    "pinui_binui",
    "tama_38_1",
    "tama_38_2",
    "other",
)
project_deal_type_enum = pg_enum("project_deal_type_enum", "ownership", "combination", "tmurot", "jv", "option", "other")
project_usage_profile_enum = pg_enum(
    "project_usage_profile_enum",
    "residential_only",
    "residential_commercial",
    "residential_mixed",
)
location_confidence_enum = pg_enum("location_confidence_enum", "exact", "approximate", "city_only", "unknown")
classification_confidence_enum = pg_enum("classification_confidence_enum", "high", "medium", "low")
mapping_review_status_enum = pg_enum("mapping_review_status_enum", "pending", "reviewed", "approved", "rejected")
geometry_type_enum = pg_enum("geometry_type_enum", "point", "line", "polygon", "approximate_area")
address_source_type_enum = pg_enum("address_source_type_enum", "parser", "admin", "geocoder", "imported")
spatial_geometry_type_enum = pg_enum(
    "spatial_geometry_type_enum",
    "exact_point",
    "approximate_point",
    "address_range",
    "polygon",
    "area",
    "city_centroid",
    "unknown",
)
geometry_source_enum = pg_enum(
    "geometry_source_enum",
    "reported",
    "geocoded",
    "manual_override",
    "city_registry",
    "inferred",
    "unknown",
)
geocoding_status_enum = pg_enum(
    "geocoding_status_enum",
    "not_started",
    "normalized",
    "geocoded",
    "failed",
    "manual_override",
)
project_status_enum = pg_enum("project_status_enum", "planning", "permit", "construction", "marketing", "completed", "stalled")
permit_status_enum = pg_enum("permit_status_enum", "none", "pending", "granted", "partial")
provenance_entity_type_enum = pg_enum("provenance_entity_type_enum", "project_master", "snapshot", "land_reserve", "address")
extraction_method_enum = pg_enum("extraction_method_enum", "table", "text", "rule", "llm", "admin")
review_status_enum = pg_enum("review_status_enum", "pending", "approved", "corrected", "rejected")
value_origin_type_enum = pg_enum("value_origin_type_enum", "reported", "inferred", "manual", "imported", "unknown")
alias_source_type_enum = pg_enum("alias_source_type_enum", "manual", "source", "system")
match_suggestion_state_enum = pg_enum("match_suggestion_state_enum", "exact", "likely", "ambiguous", "no_match")
duplicate_review_status_enum = pg_enum("duplicate_review_status_enum", "open", "merged", "dismissed")
coverage_priority_enum = pg_enum("coverage_priority_enum", "high", "medium", "low")
historical_coverage_status_enum = pg_enum(
    "historical_coverage_status_enum",
    "not_started",
    "partial",
    "current_only",
    "historical_complete",
)
snapshot_chronology_status_enum = pg_enum("snapshot_chronology_status_enum", "ok", "out_of_order", "duplicate_date")
candidate_match_status_enum = pg_enum(
    "candidate_match_status_enum",
    "unmatched",
    "matched_existing_project",
    "new_project_needed",
    "ambiguous_match",
    "ignored",
)
staging_publish_status_enum = pg_enum(
    "staging_publish_status_enum",
    "draft",
    "in_review",
    "partially_approved",
    "published",
    "rejected",
)
review_queue_status_enum = pg_enum("review_queue_status_enum", "open", "in_progress", "done", "ignored")
review_queue_entity_type_enum = pg_enum(
    "review_queue_entity_type_enum",
    "report",
    "candidate",
    "field_candidate",
    "address_candidate",
)
external_layer_geometry_type_enum = pg_enum(
    "external_layer_geometry_type_enum",
    "point",
    "line",
    "polygon",
    "mixed",
)
external_layer_update_cadence_enum = pg_enum(
    "external_layer_update_cadence_enum",
    "ad_hoc",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
)
external_layer_visibility_enum = pg_enum(
    "external_layer_visibility_enum",
    "public",
    "admin_only",
    "hidden",
)
external_relation_method_enum = pg_enum(
    "external_relation_method_enum",
    "address_based",
    "geometry_overlap",
    "manual_linkage",
)
external_relation_status_enum = pg_enum(
    "external_relation_status_enum",
    "suggested",
    "confirmed",
    "rejected",
)
parser_run_status_enum = pg_enum(
    "parser_run_status_enum",
    "queued",
    "running",
    "succeeded",
    "partial",
    "failed",
)


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name_he: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text)
    ticker: Mapped[str | None] = mapped_column(Text)
    public_status: Mapped[str] = mapped_column(company_public_status_enum, nullable=False, default="public")
    sector: Mapped[str] = mapped_column(company_sector_enum, nullable=False, default="residential_developer")

    reports: Mapped[list["Report"]] = relationship(back_populates="company")
    projects: Mapped[list["ProjectMaster"]] = relationship(back_populates="company")
    staging_reports: Mapped[list["StagingReport"]] = relationship(back_populates="company")
    staging_candidates: Mapped[list["StagingProjectCandidate"]] = relationship(back_populates="company")
    coverage_registry: Mapped["CompanyCoverageRegistry | None"] = relationship(back_populates="company")


class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(pg_enum("admin_user_role_enum", "admin", "super_admin"), nullable=False, default="admin")
    password_hash: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    report_type: Mapped[str] = mapped_column(report_type_enum, nullable=False)
    period_type: Mapped[str] = mapped_column(report_period_type_enum, nullable=False)
    period_start_date: Mapped[date | None] = mapped_column(Date)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    publish_date: Mapped[date | None] = mapped_column(Date)
    filing_reference: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_file_path: Mapped[str | None] = mapped_column(Text)
    source_is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_label: Mapped[str | None] = mapped_column(Text)
    ingestion_status: Mapped[str] = mapped_column(report_ingestion_status_enum, nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(report_status_enum, nullable=False, default="published")

    company: Mapped["Company"] = relationship(back_populates="reports")
    project_snapshots: Mapped[list["ProjectSnapshot"]] = relationship(back_populates="report")
    provenance_rows: Mapped[list["FieldProvenance"]] = relationship(back_populates="report")
    staging_report: Mapped["StagingReport | None"] = relationship(back_populates="report")
    review_queue_items: Mapped[list["ReviewQueueItem"]] = relationship(back_populates="report")
    parser_runs: Mapped[list["ParserRunLog"]] = relationship(back_populates="report")


class ProjectMaster(TimestampMixin, Base):
    __tablename__ = "project_master"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text)
    neighborhood: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    asset_domain: Mapped[str] = mapped_column(asset_domain_enum, nullable=False, default="residential_only")
    project_business_type: Mapped[str] = mapped_column(project_business_type_enum, nullable=False)
    government_program_type: Mapped[str] = mapped_column(government_program_type_enum, nullable=False, default="none")
    project_urban_renewal_type: Mapped[str] = mapped_column(project_urban_renewal_type_enum, nullable=False, default="none")
    project_deal_type: Mapped[str] = mapped_column(project_deal_type_enum, nullable=False, default="ownership")
    project_usage_profile: Mapped[str] = mapped_column(project_usage_profile_enum, nullable=False, default="residential_only")
    is_publicly_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    location_confidence: Mapped[str] = mapped_column(location_confidence_enum, nullable=False, default="unknown")
    classification_confidence: Mapped[str] = mapped_column(classification_confidence_enum, nullable=False, default="medium")
    mapping_review_status: Mapped[str] = mapped_column(mapping_review_status_enum, nullable=False, default="pending")
    source_conflict_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes_internal: Mapped[str | None] = mapped_column(Text)
    display_geometry_type: Mapped[str] = mapped_column(spatial_geometry_type_enum, nullable=False, default="unknown")
    display_geometry_source: Mapped[str] = mapped_column(geometry_source_enum, nullable=False, default="unknown")
    display_geometry_confidence: Mapped[str] = mapped_column(location_confidence_enum, nullable=False, default="unknown")
    display_geometry_geojson: Mapped[dict | None] = mapped_column(JSONB)
    display_center_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    display_center_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    display_address_summary: Mapped[str | None] = mapped_column(Text)
    display_geometry_note: Mapped[str | None] = mapped_column(Text)
    merged_into_project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="SET NULL"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship(back_populates="projects")
    aliases: Mapped[list["ProjectAlias"]] = relationship(back_populates="project")
    addresses: Mapped[list["ProjectAddress"]] = relationship(back_populates="project")
    snapshots: Mapped[list["ProjectSnapshot"]] = relationship(back_populates="project")
    merged_into_project: Mapped["ProjectMaster | None"] = relationship(remote_side="ProjectMaster.id")


class ProjectAlias(TimestampMixin, Base):
    __tablename__ = "project_aliases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias_name: Mapped[str] = mapped_column(Text, nullable=False)
    value_origin_type: Mapped[str] = mapped_column(value_origin_type_enum, nullable=False, default="manual")
    alias_source_type: Mapped[str] = mapped_column(alias_source_type_enum, nullable=False, default="manual")
    source_report_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    project: Mapped["ProjectMaster"] = relationship(back_populates="aliases")


class ProjectAddress(TimestampMixin, Base):
    __tablename__ = "project_addresses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        nullable=False,
    )
    address_text_raw: Mapped[str | None] = mapped_column(Text)
    street: Mapped[str | None] = mapped_column(Text)
    house_number_from: Mapped[int | None] = mapped_column(Integer)
    house_number_to: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(Text)
    postal_code: Mapped[str | None] = mapped_column(Text)
    normalized_address_text: Mapped[str | None] = mapped_column(Text)
    normalized_street: Mapped[str | None] = mapped_column(Text)
    normalized_city: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geometry_type: Mapped[str] = mapped_column(geometry_type_enum, nullable=False, default="point")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    location_confidence: Mapped[str] = mapped_column(location_confidence_enum, nullable=False, default="unknown")
    source_type: Mapped[str] = mapped_column(address_source_type_enum, nullable=False, default="imported")
    geometry_source: Mapped[str] = mapped_column(geometry_source_enum, nullable=False, default="unknown")
    geocoding_status: Mapped[str] = mapped_column(geocoding_status_enum, nullable=False, default="not_started")
    geocoding_provider: Mapped[str | None] = mapped_column(Text)
    geocoding_query: Mapped[str | None] = mapped_column(Text)
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    geocoding_note: Mapped[str | None] = mapped_column(Text)
    assigned_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("admin_users.id"))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["ProjectMaster"] = relationship(back_populates="addresses")


class ProjectSnapshot(TimestampMixin, Base):
    __tablename__ = "project_snapshots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    project_status: Mapped[str | None] = mapped_column(project_status_enum)
    permit_status: Mapped[str | None] = mapped_column(permit_status_enum)
    planning_status: Mapped[str | None] = mapped_column(Text)
    signature_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    engineering_completion_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    financial_completion_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    total_units: Mapped[int | None] = mapped_column(Integer)
    marketed_units: Mapped[int | None] = mapped_column(Integer)
    sold_units_period: Mapped[int | None] = mapped_column(Integer)
    sold_units_cumulative: Mapped[int | None] = mapped_column(Integer)
    unsold_units: Mapped[int | None] = mapped_column(Integer)
    sold_area_sqm_period: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    sold_area_sqm_cumulative: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    unsold_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    avg_price_per_sqm_period: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    avg_price_per_sqm_cumulative: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    recognized_revenue_to_date: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    expected_revenue_total: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    expected_revenue_signed_contracts: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    expected_revenue_unsold_inventory: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    gross_profit_total_expected: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    gross_profit_recognized: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    gross_profit_unrecognized: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    gross_margin_expected_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    expected_pre_tax_profit: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    land_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    development_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    finance_cost_capitalized: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    other_project_costs: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    advances_received: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    receivables_from_signed_contracts: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    estimated_start_date: Mapped[date | None] = mapped_column(Date)
    estimated_completion_date: Mapped[date | None] = mapped_column(Date)
    needs_admin_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    chronology_status: Mapped[str] = mapped_column(snapshot_chronology_status_enum, nullable=False, default="ok")
    chronology_notes: Mapped[str | None] = mapped_column(Text)
    notes_internal: Mapped[str | None] = mapped_column(Text)

    project: Mapped["ProjectMaster"] = relationship(back_populates="snapshots")
    report: Mapped["Report"] = relationship(back_populates="project_snapshots")


class FieldProvenance(Base):
    __tablename__ = "field_provenance"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    entity_type: Mapped[str] = mapped_column(provenance_entity_type_enum, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    source_report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_section: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(extraction_method_enum, nullable=False)
    parser_version: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    value_origin_type: Mapped[str] = mapped_column(value_origin_type_enum, nullable=False, default="reported")
    review_status: Mapped[str] = mapped_column(review_status_enum, nullable=False, default="approved")
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("admin_users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    report: Mapped["Report"] = relationship(back_populates="provenance_rows")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("admin_users.id"))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    diff_json: Mapped[dict | None] = mapped_column(JSONB)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StagingReport(TimestampMixin, Base):
    __tablename__ = "staging_reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    publish_status: Mapped[str] = mapped_column(staging_publish_status_enum, nullable=False, default="draft")
    review_status: Mapped[str] = mapped_column(review_status_enum, nullable=False, default="pending")
    notes_internal: Mapped[str | None] = mapped_column(Text)

    report: Mapped["Report"] = relationship(back_populates="staging_report")
    company: Mapped["Company"] = relationship(back_populates="staging_reports")
    parser_runs: Mapped[list["ParserRunLog"]] = relationship(back_populates="staging_report")
    sections: Mapped[list["StagingSection"]] = relationship(back_populates="staging_report")
    candidates: Mapped[list["StagingProjectCandidate"]] = relationship(back_populates="staging_report")


class StagingSection(TimestampMixin, Base):
    __tablename__ = "staging_sections"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    staging_report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    parser_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parser_run_logs.id", ondelete="SET NULL"),
    )
    section_name: Mapped[str] = mapped_column(Text, nullable=False)
    raw_label: Mapped[str | None] = mapped_column(Text)
    source_page_from: Mapped[int | None] = mapped_column(Integer)
    source_page_to: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    staging_report: Mapped["StagingReport"] = relationship(back_populates="sections")
    parser_run: Mapped["ParserRunLog | None"] = relationship(back_populates="sections")
    candidates: Mapped[list["StagingProjectCandidate"]] = relationship(back_populates="staging_section")


class StagingProjectCandidate(TimestampMixin, Base):
    __tablename__ = "staging_project_candidates"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    staging_report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    parser_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parser_run_logs.id", ondelete="SET NULL"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    staging_section_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_sections.id", ondelete="SET NULL"),
    )
    matched_project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="SET NULL"),
    )
    candidate_project_name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text)
    neighborhood: Mapped[str | None] = mapped_column(Text)
    project_business_type: Mapped[str | None] = mapped_column(project_business_type_enum)
    government_program_type: Mapped[str] = mapped_column(government_program_type_enum, nullable=False, default="none")
    project_urban_renewal_type: Mapped[str] = mapped_column(project_urban_renewal_type_enum, nullable=False, default="none")
    project_status: Mapped[str | None] = mapped_column(project_status_enum)
    permit_status: Mapped[str | None] = mapped_column(permit_status_enum)
    total_units: Mapped[int | None] = mapped_column(Integer)
    marketed_units: Mapped[int | None] = mapped_column(Integer)
    sold_units_cumulative: Mapped[int | None] = mapped_column(Integer)
    unsold_units: Mapped[int | None] = mapped_column(Integer)
    avg_price_per_sqm_cumulative: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    gross_profit_total_expected: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    gross_margin_expected_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    location_confidence: Mapped[str] = mapped_column(location_confidence_enum, nullable=False, default="unknown")
    value_origin_type: Mapped[str] = mapped_column(value_origin_type_enum, nullable=False, default="manual")
    confidence_level: Mapped[str] = mapped_column(classification_confidence_enum, nullable=False, default="medium")
    matching_status: Mapped[str] = mapped_column(candidate_match_status_enum, nullable=False, default="unmatched")
    publish_status: Mapped[str] = mapped_column(staging_publish_status_enum, nullable=False, default="draft")
    review_status: Mapped[str] = mapped_column(review_status_enum, nullable=False, default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text)
    diff_summary: Mapped[dict | None] = mapped_column(JSONB)

    staging_report: Mapped["StagingReport"] = relationship(back_populates="candidates")
    parser_run: Mapped["ParserRunLog | None"] = relationship(back_populates="candidates")
    staging_section: Mapped["StagingSection | None"] = relationship(back_populates="candidates")
    company: Mapped["Company"] = relationship(back_populates="staging_candidates")
    matched_project: Mapped["ProjectMaster | None"] = relationship()
    field_candidates: Mapped[list["StagingFieldCandidate"]] = relationship(back_populates="candidate")
    address_candidates: Mapped[list["StagingAddressCandidate"]] = relationship(back_populates="candidate")
    review_queue_items: Mapped[list["ReviewQueueItem"]] = relationship(back_populates="candidate")
    match_suggestions: Mapped[list["CandidateMatchSuggestion"]] = relationship(back_populates="candidate")


class StagingFieldCandidate(TimestampMixin, Base):
    __tablename__ = "staging_field_candidates"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_project_candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_section: Mapped[str | None] = mapped_column(Text)
    value_origin_type: Mapped[str] = mapped_column(value_origin_type_enum, nullable=False, default="manual")
    confidence_level: Mapped[str] = mapped_column(classification_confidence_enum, nullable=False, default="medium")
    review_status: Mapped[str] = mapped_column(review_status_enum, nullable=False, default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped["StagingProjectCandidate"] = relationship(back_populates="field_candidates")


class StagingAddressCandidate(TimestampMixin, Base):
    __tablename__ = "staging_address_candidates"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_project_candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    address_text_raw: Mapped[str | None] = mapped_column(Text)
    street: Mapped[str | None] = mapped_column(Text)
    house_number_from: Mapped[int | None] = mapped_column(Integer)
    house_number_to: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    location_confidence: Mapped[str] = mapped_column(location_confidence_enum, nullable=False, default="unknown")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    value_origin_type: Mapped[str] = mapped_column(value_origin_type_enum, nullable=False, default="manual")
    confidence_level: Mapped[str] = mapped_column(classification_confidence_enum, nullable=False, default="medium")
    review_status: Mapped[str] = mapped_column(review_status_enum, nullable=False, default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped["StagingProjectCandidate"] = relationship(back_populates="address_candidates")


class ReviewQueueItem(TimestampMixin, Base):
    __tablename__ = "review_queue_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    entity_type: Mapped[str] = mapped_column(review_queue_entity_type_enum, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    report_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"))
    candidate_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_project_candidates.id", ondelete="CASCADE"),
    )
    status: Mapped[str] = mapped_column(review_queue_status_enum, nullable=False, default="open")
    notes: Mapped[str | None] = mapped_column(Text)

    report: Mapped["Report | None"] = relationship(back_populates="review_queue_items")
    candidate: Mapped["StagingProjectCandidate | None"] = relationship(back_populates="review_queue_items")


class CandidateMatchSuggestion(TimestampMixin, Base):
    __tablename__ = "candidate_match_suggestions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_project_candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    suggested_project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="CASCADE"),
    )
    match_state: Mapped[str] = mapped_column(match_suggestion_state_enum, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    reasons_json: Mapped[dict | None] = mapped_column(JSONB)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    candidate: Mapped["StagingProjectCandidate"] = relationship(back_populates="match_suggestions")
    suggested_project: Mapped["ProjectMaster | None"] = relationship()


class ProjectDuplicateSuggestion(TimestampMixin, Base):
    __tablename__ = "project_duplicate_suggestions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        nullable=False,
    )
    duplicate_project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_state: Mapped[str] = mapped_column(match_suggestion_state_enum, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    reasons_json: Mapped[dict | None] = mapped_column(JSONB)
    review_status: Mapped[str] = mapped_column(duplicate_review_status_enum, nullable=False, default="open")
    reviewed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectMergeLog(Base):
    __tablename__ = "project_merge_log"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    winner_project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    loser_project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="RESTRICT"),
        nullable=False,
    )
    merged_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"))
    merge_reason: Mapped[str | None] = mapped_column(Text)
    summary_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CompanyCoverageRegistry(TimestampMixin, Base):
    __tablename__ = "company_coverage_registry"

    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_in_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    out_of_scope_reason: Mapped[str | None] = mapped_column(Text)
    coverage_priority: Mapped[str] = mapped_column(coverage_priority_enum, nullable=False, default="medium")
    latest_report_ingested_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
    )
    historical_coverage_status: Mapped[str] = mapped_column(
        historical_coverage_status_enum,
        nullable=False,
        default="not_started",
    )
    notes: Mapped[str | None] = mapped_column(Text)

    company: Mapped["Company"] = relationship(back_populates="coverage_registry")


class ExternalLayer(TimestampMixin, Base):
    __tablename__ = "external_layers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    layer_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    geometry_type: Mapped[str] = mapped_column(external_layer_geometry_type_enum, nullable=False, default="point")
    update_cadence: Mapped[str] = mapped_column(external_layer_update_cadence_enum, nullable=False, default="ad_hoc")
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    visibility: Mapped[str] = mapped_column(external_layer_visibility_enum, nullable=False, default="public")
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_on_map: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    records: Mapped[list["ExternalLayerRecord"]] = relationship(back_populates="layer")


class ExternalLayerRecord(TimestampMixin, Base):
    __tablename__ = "external_layer_records"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    layer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("external_layers.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_record_id: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    geometry_geojson: Mapped[dict | None] = mapped_column(JSONB)
    display_center_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    display_center_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    properties_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    effective_date: Mapped[date | None] = mapped_column(Date)
    source_metadata: Mapped[dict | None] = mapped_column(JSONB)
    update_metadata: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    layer: Mapped["ExternalLayer"] = relationship(back_populates="records")
    project_relations: Mapped[list["ExternalLayerProjectRelation"]] = relationship(back_populates="record")


class ExternalLayerProjectRelation(TimestampMixin, Base):
    __tablename__ = "external_layer_project_relations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    external_layer_record_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("external_layer_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_master.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_method: Mapped[str] = mapped_column(external_relation_method_enum, nullable=False)
    confidence_level: Mapped[str] = mapped_column(classification_confidence_enum, nullable=False, default="medium")
    relation_status: Mapped[str] = mapped_column(external_relation_status_enum, nullable=False, default="suggested")
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    record: Mapped["ExternalLayerRecord"] = relationship(back_populates="project_relations")
    project: Mapped["ProjectMaster"] = relationship()


class ParserRunLog(TimestampMixin, Base):
    __tablename__ = "parser_run_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    report_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    staging_report_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staging_reports.id", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(parser_run_status_enum, nullable=False, default="queued")
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    source_label: Mapped[str | None] = mapped_column(Text)
    source_reference: Mapped[str | None] = mapped_column(Text)
    source_checksum: Mapped[str | None] = mapped_column(Text)
    sections_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    field_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    address_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    errors_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    diagnostics_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    report: Mapped["Report"] = relationship(back_populates="parser_runs")
    staging_report: Mapped["StagingReport | None"] = relationship(back_populates="parser_runs")
    sections: Mapped[list["StagingSection"]] = relationship(back_populates="parser_run")
    candidates: Mapped[list["StagingProjectCandidate"]] = relationship(back_populates="parser_run")
