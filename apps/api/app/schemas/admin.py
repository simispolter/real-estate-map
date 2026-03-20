from pydantic import BaseModel, Field


class AdminOverviewResponse(BaseModel):
    pending_reports: int = Field(default=0, ge=0)
    pending_reviews: int = Field(default=0, ge=0)
    pending_location_assignments: int = Field(default=0, ge=0)
    pending_publish_candidates: int = Field(default=0, ge=0)
