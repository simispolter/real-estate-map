from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.admin import (
    AdminAddressUpsertRequest,
    AdminAnomaliesResponse,
    AdminCoverageDashboardResponse,
    AdminCoverageBulkRequest,
    AdminCoverageBulkResponse,
    AdminCoverageGapsResponse,
    AdminCoverageReportsResponse,
    AdminCoverageUpdateRequest,
    AdminDuplicatesResponse,
    AdminExternalLayerCreateRequest,
    AdminExternalLayerDetailResponse,
    AdminExternalLayersResponse,
    AdminExternalLayerUpdateRequest,
    AdminIntakeListResponse,
    AdminMergeProjectsRequest,
    AdminOpsDashboardResponse,
    AdminOverviewResponse,
    AdminLocationReviewResponse,
    AdminProjectAliasCreateRequest,
    AdminProjectDetailResponse,
    AdminProjectSnapshotsResponse,
    AdminProjectsListResponse,
    AdminProjectCreateRequest,
    AdminProjectDisplayGeometryUpdateRequest,
    AdminProjectUpdateRequest,
    AdminSnapshotCreateRequest,
    AdminSnapshotUpdateRequest,
)
from app.schemas.ingestion import AdminCandidateDetailResponse
from app.services.coverage_ops import (
    apply_coverage_bulk_action,
    export_coverage_rows,
    get_coverage_dashboard,
    list_coverage_gaps,
    list_coverage_reports,
    list_location_review_projects,
    update_company_coverage,
)
from app.services.external_layers import (
    create_admin_external_layer,
    get_admin_external_layer_detail,
    list_admin_external_layers,
    update_admin_external_layer,
)
from app.services.quality_ops import get_admin_ops_dashboard, list_admin_anomalies
from app.services.admin_review import (
    add_project_alias,
    create_admin_project,
    create_project_snapshot,
    delete_project_address,
    delete_project_alias,
    geocode_admin_project_address,
    get_admin_project_detail,
    get_intake_candidate_detail,
    list_admin_duplicates,
    list_admin_projects,
    list_intake_candidates,
    list_project_snapshots,
    merge_admin_projects,
    normalize_admin_project_address,
    update_admin_project,
    update_project_display_geometry,
    update_snapshot,
    upsert_project_address,
)

router = APIRouter()


@router.get("/overview", response_model=AdminOverviewResponse)
async def get_admin_overview() -> AdminOverviewResponse:
    return AdminOverviewResponse(
        pending_reports=0,
        pending_reviews=0,
        pending_location_assignments=0,
        pending_publish_candidates=0,
    )


@router.get("/projects", response_model=AdminProjectsListResponse)
async def get_admin_projects(
    q: str | None = None,
    company_id: UUID | None = None,
    city: str | None = None,
    project_business_type: str | None = None,
    government_program_type: str | None = None,
    project_urban_renewal_type: str | None = None,
    visibility: str | None = Query(default=None, pattern="^(public|internal)$"),
    location_confidence: str | None = None,
    sort_by: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectsListResponse:
    filters = {
        "q": q,
        "company_id": str(company_id) if company_id else None,
        "city": city,
        "project_business_type": project_business_type,
        "government_program_type": government_program_type,
        "project_urban_renewal_type": project_urban_renewal_type,
        "visibility": visibility,
        "location_confidence": location_confidence,
        "sort_by": sort_by,
    }
    return AdminProjectsListResponse(items=await list_admin_projects(session, filters))


@router.post("/projects", response_model=AdminProjectDetailResponse)
async def post_admin_project(
    payload: AdminProjectCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    return AdminProjectDetailResponse.model_validate(await create_admin_project(session, payload.model_dump()))


@router.get("/projects/{project_id}", response_model=AdminProjectDetailResponse)
async def get_admin_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await get_admin_project_detail(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.patch("/projects/{project_id}", response_model=AdminProjectDetailResponse)
async def patch_admin_project(
    project_id: UUID,
    payload: AdminProjectUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await update_admin_project(session, project_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.post("/projects/{project_id}/aliases", response_model=AdminProjectDetailResponse)
async def post_admin_project_alias(
    project_id: UUID,
    payload: AdminProjectAliasCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await add_project_alias(session, project_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.delete("/projects/{project_id}/aliases/{alias_id}", response_model=AdminProjectDetailResponse)
async def remove_admin_project_alias(
    project_id: UUID,
    alias_id: UUID,
    reviewer_note: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await delete_project_alias(session, project_id, alias_id, reviewer_note)
    if project is None:
        raise HTTPException(status_code=404, detail="Project or alias not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.get("/projects/{project_id}/snapshots", response_model=AdminProjectSnapshotsResponse)
async def get_admin_project_snapshots(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectSnapshotsResponse:
    items = await list_project_snapshots(session, project_id)
    if items is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectSnapshotsResponse(project_id=project_id, items=items)


@router.post("/projects/{project_id}/snapshots", response_model=AdminProjectDetailResponse)
async def post_admin_project_snapshot(
    project_id: UUID,
    payload: AdminSnapshotCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await create_project_snapshot(session, project_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Project or report not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.patch("/snapshots/{snapshot_id}", response_model=AdminProjectDetailResponse)
async def patch_admin_snapshot(
    snapshot_id: UUID,
    payload: AdminSnapshotUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await update_snapshot(session, snapshot_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.post("/projects/{project_id}/addresses", response_model=AdminProjectDetailResponse)
async def create_admin_project_address(
    project_id: UUID,
    payload: AdminAddressUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await upsert_project_address(session, project_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.put("/projects/{project_id}/addresses/{address_id}", response_model=AdminProjectDetailResponse)
async def update_admin_project_address(
    project_id: UUID,
    address_id: UUID,
    payload: AdminAddressUpsertRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await upsert_project_address(session, project_id, payload.model_dump(exclude_unset=True), address_id=address_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project or address not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.delete("/projects/{project_id}/addresses/{address_id}", response_model=AdminProjectDetailResponse)
async def remove_admin_project_address(
    project_id: UUID,
    address_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await delete_project_address(session, project_id, address_id, reason="Deleted from admin review")
    if project is None:
        raise HTTPException(status_code=404, detail="Project or address not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.post("/projects/{project_id}/addresses/{address_id}/normalize", response_model=AdminProjectDetailResponse)
async def normalize_admin_address(
    project_id: UUID,
    address_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await normalize_admin_project_address(session, project_id, address_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project or address not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.post("/projects/{project_id}/addresses/{address_id}/geocode", response_model=AdminProjectDetailResponse)
async def geocode_admin_address(
    project_id: UUID,
    address_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await geocode_admin_project_address(session, project_id, address_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project or address not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.patch("/projects/{project_id}/display-geometry", response_model=AdminProjectDetailResponse)
async def patch_admin_project_display_geometry(
    project_id: UUID,
    payload: AdminProjectDisplayGeometryUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await update_project_display_geometry(session, project_id, payload.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return AdminProjectDetailResponse.model_validate(project)


@router.get("/intake", response_model=AdminIntakeListResponse)
async def get_admin_intake(
    q: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> AdminIntakeListResponse:
    return AdminIntakeListResponse(items=await list_intake_candidates(session, {"q": q}))


@router.get("/intake/{candidate_id}", response_model=AdminCandidateDetailResponse)
async def get_admin_intake_candidate(
    candidate_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCandidateDetailResponse:
    candidate = await get_intake_candidate_detail(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return AdminCandidateDetailResponse.model_validate(candidate)


@router.get("/duplicates", response_model=AdminDuplicatesResponse)
async def get_admin_duplicates(
    session: AsyncSession = Depends(get_db_session),
) -> AdminDuplicatesResponse:
    return AdminDuplicatesResponse(items=await list_admin_duplicates(session))


@router.get("/anomalies", response_model=AdminAnomaliesResponse)
async def get_admin_anomalies(
    session: AsyncSession = Depends(get_db_session),
) -> AdminAnomaliesResponse:
    return AdminAnomaliesResponse(items=await list_admin_anomalies(session))


@router.get("/ops", response_model=AdminOpsDashboardResponse)
async def get_admin_ops(
    session: AsyncSession = Depends(get_db_session),
) -> AdminOpsDashboardResponse:
    return AdminOpsDashboardResponse.model_validate(await get_admin_ops_dashboard(session))


@router.post("/projects/merge", response_model=AdminProjectDetailResponse)
async def post_admin_project_merge(
    payload: AdminMergeProjectsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminProjectDetailResponse:
    project = await merge_admin_projects(session, payload.winner_project_id, payload.loser_project_id, payload.merge_reason)
    if project is None:
        raise HTTPException(status_code=404, detail="Projects not found or merge invalid")
    return AdminProjectDetailResponse.model_validate(project)


@router.get("/coverage", response_model=AdminCoverageDashboardResponse)
async def get_admin_coverage(
    session: AsyncSession = Depends(get_db_session),
) -> AdminCoverageDashboardResponse:
    return AdminCoverageDashboardResponse.model_validate(await get_coverage_dashboard(session))


@router.get("/coverage/companies", response_model=AdminCoverageDashboardResponse)
async def get_admin_coverage_companies(
    session: AsyncSession = Depends(get_db_session),
) -> AdminCoverageDashboardResponse:
    return AdminCoverageDashboardResponse.model_validate(await get_coverage_dashboard(session))


@router.get("/coverage/reports", response_model=AdminCoverageReportsResponse)
async def get_admin_coverage_reports(
    company_id: UUID | None = None,
    ingestion_status: str | None = None,
    scope: str | None = Query(default=None, pattern="^(in_scope|out_of_scope)$"),
    published: str | None = Query(default=None, pattern="^(yes|no)$"),
    session: AsyncSession = Depends(get_db_session),
) -> AdminCoverageReportsResponse:
    return AdminCoverageReportsResponse(
        items=await list_coverage_reports(
            session,
            {
                "company_id": str(company_id) if company_id else None,
                "ingestion_status": ingestion_status,
                "scope": scope,
                "published": published,
            },
        )
    )


@router.get("/coverage/gaps", response_model=AdminCoverageGapsResponse)
async def get_admin_coverage_gaps(
    company_id: UUID | None = None,
    city: str | None = None,
    location_confidence: str | None = None,
    backfill_status: str | None = None,
    missing_group: str | None = Query(default=None, pattern="^(location|metrics|stale)$"),
    session: AsyncSession = Depends(get_db_session),
) -> AdminCoverageGapsResponse:
    return AdminCoverageGapsResponse.model_validate(
        await list_coverage_gaps(
            session,
            {
                "company_id": str(company_id) if company_id else None,
                "city": city,
                "location_confidence": location_confidence,
                "backfill_status": backfill_status,
                "missing_group": missing_group,
            },
        )
    )


@router.post("/coverage/bulk", response_model=AdminCoverageBulkResponse)
async def post_admin_coverage_bulk(
    payload: AdminCoverageBulkRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCoverageBulkResponse:
    return AdminCoverageBulkResponse.model_validate(
        await apply_coverage_bulk_action(session, payload.model_dump(exclude_unset=True))
    )


@router.get("/coverage/export")
async def get_admin_coverage_export(
    kind: str = Query(pattern="^(gaps|metrics_missing|location_missing|reports)$"),
    company_id: UUID | None = None,
    city: str | None = None,
    location_confidence: str | None = None,
    backfill_status: str | None = None,
    missing_group: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    csv_payload, filename = await export_coverage_rows(
        session,
        kind,
        {
            "company_id": str(company_id) if company_id else None,
            "city": city,
            "location_confidence": location_confidence,
            "backfill_status": backfill_status,
            "missing_group": missing_group,
        },
    )
    return Response(
        content=csv_payload,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/coverage/{company_id}", response_model=AdminCoverageDashboardResponse)
async def patch_admin_coverage_company(
    company_id: UUID,
    payload: AdminCoverageUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCoverageDashboardResponse:
    dashboard = await update_company_coverage(session, company_id, payload.model_dump(exclude_unset=True))
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return AdminCoverageDashboardResponse.model_validate(dashboard)


@router.get("/location-review/projects", response_model=AdminLocationReviewResponse)
async def get_admin_location_review(
    company_id: UUID | None = None,
    city: str | None = None,
    location_confidence: str | None = None,
    backfill_status: str | None = None,
    missing_fields: str | None = Query(default=None, pattern="^(yes|no)$"),
    include_all: bool = False,
    session: AsyncSession = Depends(get_db_session),
) -> AdminLocationReviewResponse:
    return AdminLocationReviewResponse.model_validate(
        await list_location_review_projects(
            session,
            {
                "company_id": str(company_id) if company_id else None,
                "city": city,
                "location_confidence": location_confidence,
                "backfill_status": backfill_status,
                "missing_fields": missing_fields,
                "include_all": include_all,
            },
        )
    )


@router.get("/layers", response_model=AdminExternalLayersResponse)
async def get_admin_layers(
    session: AsyncSession = Depends(get_db_session),
) -> AdminExternalLayersResponse:
    return AdminExternalLayersResponse(items=await list_admin_external_layers(session))


@router.post("/layers", response_model=AdminExternalLayerDetailResponse)
async def post_admin_layer(
    payload: AdminExternalLayerCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminExternalLayerDetailResponse:
    return AdminExternalLayerDetailResponse.model_validate(
        await create_admin_external_layer(session, payload.model_dump(exclude_unset=True))
    )


@router.get("/layers/{layer_id}", response_model=AdminExternalLayerDetailResponse)
async def get_admin_layer(
    layer_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminExternalLayerDetailResponse:
    layer = await get_admin_external_layer_detail(session, layer_id)
    if layer is None:
        raise HTTPException(status_code=404, detail="Layer not found")
    return AdminExternalLayerDetailResponse.model_validate(layer)


@router.patch("/layers/{layer_id}", response_model=AdminExternalLayerDetailResponse)
async def patch_admin_layer(
    layer_id: UUID,
    payload: AdminExternalLayerUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminExternalLayerDetailResponse:
    layer = await update_admin_external_layer(session, layer_id, payload.model_dump(exclude_unset=True))
    if layer is None:
        raise HTTPException(status_code=404, detail="Layer not found")
    return AdminExternalLayerDetailResponse.model_validate(layer)
