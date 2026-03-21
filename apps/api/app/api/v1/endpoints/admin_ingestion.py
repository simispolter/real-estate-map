from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.ingestion import (
    AdminCandidateCreateRequest,
    AdminCandidateDetailResponse,
    AdminCandidateMatchRequest,
    AdminCandidatePublishRequest,
    AdminCandidateUpdateRequest,
    AdminReportCandidatesResponse,
    AdminReportCreateRequest,
    AdminReportDetailResponse,
    AdminReportsListResponse,
    AdminReportUpdateRequest,
)
from app.services.ingestion import (
    create_admin_report,
    create_candidate,
    get_admin_report_detail,
    get_candidate_detail,
    list_admin_reports,
    list_report_candidates,
    match_candidate,
    publish_candidate,
    update_admin_report,
    update_candidate,
)

router = APIRouter()


@router.get("/reports", response_model=AdminReportsListResponse)
async def get_admin_reports(
    session: AsyncSession = Depends(get_db_session),
) -> AdminReportsListResponse:
    return AdminReportsListResponse(items=await list_admin_reports(session))


@router.post("/reports", response_model=AdminReportDetailResponse)
async def post_admin_report(
    payload: AdminReportCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminReportDetailResponse:
    return AdminReportDetailResponse.model_validate(await create_admin_report(session, payload.model_dump()))


@router.get("/reports/{report_id}", response_model=AdminReportDetailResponse)
async def get_admin_report(
    report_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminReportDetailResponse:
    report = await get_admin_report_detail(session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return AdminReportDetailResponse.model_validate(report)


@router.patch("/reports/{report_id}", response_model=AdminReportDetailResponse)
async def patch_admin_report(
    report_id: UUID,
    payload: AdminReportUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminReportDetailResponse:
    report = await update_admin_report(session, report_id, payload.model_dump(exclude_unset=True))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return AdminReportDetailResponse.model_validate(report)


@router.get("/reports/{report_id}/candidates", response_model=AdminReportCandidatesResponse)
async def get_admin_report_candidates(
    report_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminReportCandidatesResponse:
    return AdminReportCandidatesResponse(report_id=report_id, items=await list_report_candidates(session, report_id))


@router.post("/reports/{report_id}/candidates", response_model=AdminCandidateDetailResponse)
async def post_admin_candidate(
    report_id: UUID,
    payload: AdminCandidateCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCandidateDetailResponse:
    candidate = await create_candidate(session, report_id, payload.model_dump())
    if candidate is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return AdminCandidateDetailResponse.model_validate(candidate)


@router.get("/candidates/{candidate_id}", response_model=AdminCandidateDetailResponse)
async def get_admin_candidate(
    candidate_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCandidateDetailResponse:
    candidate = await get_candidate_detail(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return AdminCandidateDetailResponse.model_validate(candidate)


@router.patch("/candidates/{candidate_id}", response_model=AdminCandidateDetailResponse)
async def patch_admin_candidate(
    candidate_id: UUID,
    payload: AdminCandidateUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCandidateDetailResponse:
    candidate = await update_candidate(session, candidate_id, payload.model_dump(exclude_unset=True))
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return AdminCandidateDetailResponse.model_validate(candidate)


@router.post("/candidates/{candidate_id}/match", response_model=AdminCandidateDetailResponse)
async def post_admin_candidate_match(
    candidate_id: UUID,
    payload: AdminCandidateMatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCandidateDetailResponse:
    candidate = await match_candidate(session, candidate_id, payload.model_dump())
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return AdminCandidateDetailResponse.model_validate(candidate)


@router.post("/candidates/{candidate_id}/publish", response_model=AdminCandidateDetailResponse)
async def post_admin_candidate_publish(
    candidate_id: UUID,
    payload: AdminCandidatePublishRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AdminCandidateDetailResponse:
    try:
        candidate = await publish_candidate(session, candidate_id, payload.reviewer_note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return AdminCandidateDetailResponse.model_validate(candidate)
