from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.public import (
    FieldProvenanceResponse,
    ProjectAddressResponse,
    ProjectClassification,
    ProjectCompanySummary,
    ProjectLocation,
    ProjectSnapshotDetail,
)


class AdminOverviewResponse(BaseModel):
    pending_reports: int = Field(default=0, ge=0)
    pending_reviews: int = Field(default=0, ge=0)
    pending_location_assignments: int = Field(default=0, ge=0)
    pending_publish_candidates: int = Field(default=0, ge=0)


class AdminProjectListItem(BaseModel):
    id: UUID
    canonical_name: str
    company: ProjectCompanySummary
    city: str | None = None
    project_business_type: str
    permit_status: str | None = None
    classification_confidence: str
    location_confidence: str
    needs_admin_review: bool
    latest_snapshot_date: str | None = None


class AdminProjectsListResponse(BaseModel):
    items: list[AdminProjectListItem] = Field(default_factory=list)


class AdminAuditLogItem(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None = None
    diff_json: dict | None = None
    comment: str | None = None
    created_at: datetime


class AdminProjectDetailResponse(BaseModel):
    id: UUID
    canonical_name: str
    company: ProjectCompanySummary
    classification: ProjectClassification
    location: ProjectLocation
    latest_snapshot: ProjectSnapshotDetail
    addresses: list[ProjectAddressResponse] = Field(default_factory=list)
    field_provenance: list[FieldProvenanceResponse] = Field(default_factory=list)
    notes_internal: str | None = None
    audit_log: list[AdminAuditLogItem] = Field(default_factory=list)


class AdminProjectUpdateRequest(BaseModel):
    project_business_type: str | None = None
    government_program_type: str | None = None
    project_urban_renewal_type: str | None = None
    permit_status: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    location_confidence: str | None = None
    notes_internal: str | None = None
    field_origin_types: dict[str, str] = Field(default_factory=dict)
    change_reason: str | None = None


class AdminAddressUpsertRequest(BaseModel):
    address_text_raw: str | None = None
    street: str | None = None
    house_number_from: int | None = None
    house_number_to: int | None = None
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    location_confidence: str = "city"
    is_primary: bool = False
    value_origin_type: str = "reported"
    change_reason: str | None = None
