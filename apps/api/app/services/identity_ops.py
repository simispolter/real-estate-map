from __future__ import annotations

from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import (
    CandidateMatchSuggestion,
    Company,
    CompanyCoverageRegistry,
    ProjectAddress,
    ProjectAlias,
    ProjectDuplicateSuggestion,
    ProjectMaster,
    ProjectSnapshot,
    Report,
    StagingAddressCandidate,
    StagingProjectCandidate,
)


KEY_PROJECT_FIELDS = (
    "project_business_type",
    "government_program_type",
    "project_urban_renewal_type",
    "project_status",
    "permit_status",
    "total_units",
    "marketed_units",
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().replace("-", " ").replace("/", " ").split())


def similarity_score(left: str | None, right: str | None) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def _address_tokens(values: list[str | None]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in normalize_text(value).split():
            if len(token) >= 2:
                tokens.add(token)
    return tokens


async def _project_alias_names(session: AsyncSession, project_id: UUID) -> list[str]:
    rows = (
        await session.execute(
            select(ProjectAlias.alias_name)
            .where(ProjectAlias.project_id == project_id, ProjectAlias.is_active.is_(True))
            .order_by(ProjectAlias.created_at.asc())
        )
    ).scalars().all()
    return [row for row in rows if row]


async def _project_address_texts(session: AsyncSession, project_id: UUID) -> list[str]:
    rows = (
        await session.execute(
            select(ProjectAddress.address_text_raw, ProjectAddress.street, ProjectAddress.city)
            .where(ProjectAddress.project_id == project_id)
            .order_by(ProjectAddress.is_primary.desc(), ProjectAddress.created_at.asc())
        )
    ).all()
    values: list[str] = []
    for address_text_raw, street, city in rows:
        values.extend([address_text_raw, street, city])
    return [value for value in values if value]


async def refresh_candidate_match_suggestions(session: AsyncSession, candidate: StagingProjectCandidate) -> list[dict]:
    await session.execute(delete(CandidateMatchSuggestion).where(CandidateMatchSuggestion.candidate_id == candidate.id))

    rows = (
        await session.execute(
            select(ProjectMaster, Company)
            .join(Company, Company.id == ProjectMaster.company_id)
            .where(
                ProjectMaster.company_id == candidate.company_id,
                ProjectMaster.deleted_at.is_(None),
                ProjectMaster.merged_into_project_id.is_(None),
                True if candidate.city is None else ProjectMaster.city == candidate.city,
            )
        )
    ).all()

    candidate_addresses = (
        await session.execute(
            select(StagingAddressCandidate).where(StagingAddressCandidate.candidate_id == candidate.id)
        )
    ).scalars().all()
    candidate_name = candidate.candidate_project_name
    candidate_address_tokens = _address_tokens(
        [address.address_text_raw for address in candidate_addresses]
        + [address.street for address in candidate_addresses]
        + [address.city for address in candidate_addresses]
    )

    suggestions: list[dict] = []
    for project, company in rows:
        aliases = await _project_alias_names(session, project.id)
        project_addresses = await _project_address_texts(session, project.id)
        name_scores = [similarity_score(candidate_name, project.canonical_name), *[similarity_score(candidate_name, alias) for alias in aliases]]
        best_name_score = max(name_scores) if name_scores else 0.0
        city_match = bool(candidate.city and project.city and normalize_text(candidate.city) == normalize_text(project.city))
        neighborhood_match = bool(
            candidate.neighborhood
            and project.neighborhood
            and normalize_text(candidate.neighborhood) == normalize_text(project.neighborhood)
        )
        project_address_tokens = _address_tokens(project_addresses)
        overlap_count = len(candidate_address_tokens & project_address_tokens)
        has_address_overlap = overlap_count > 0

        weighted = best_name_score * 0.55
        weighted += 0.20 if city_match else 0
        weighted += 0.10 if neighborhood_match else 0
        weighted += min(0.15, overlap_count * 0.05)

        if weighted >= 0.92 or (best_name_score >= 0.95 and (city_match or has_address_overlap)):
            match_state = "exact"
        elif weighted >= 0.76:
            match_state = "likely"
        elif weighted >= 0.58:
            match_state = "ambiguous"
        else:
            match_state = "no_match"

        reasons_json = {
            "company_name": company.name_he,
            "best_name_score": round(best_name_score, 3),
            "city_match": city_match,
            "neighborhood_match": neighborhood_match,
            "address_overlap_count": overlap_count,
            "alias_matches": [alias for alias in aliases if similarity_score(candidate_name, alias) >= 0.82],
        }
        suggestion = CandidateMatchSuggestion(
            id=uuid4(),
            candidate_id=candidate.id,
            suggested_project_id=project.id,
            match_state=match_state,
            score=Decimal(str(round(weighted * 100, 2))),
            reasons_json=reasons_json,
            is_selected=project.id == candidate.matched_project_id,
        )
        session.add(suggestion)
        suggestions.append(
            {
                "project_id": project.id,
                "canonical_name": project.canonical_name,
                "city": project.city,
                "neighborhood": project.neighborhood,
                "similarity_score": round(weighted, 3),
                "match_state": match_state,
                "reasons_json": reasons_json,
            }
        )

    if not suggestions:
        session.add(
            CandidateMatchSuggestion(
                id=uuid4(),
                candidate_id=candidate.id,
                suggested_project_id=None,
                match_state="no_match",
                score=Decimal("0"),
                reasons_json={"reason": "No in-company canonical projects matched the candidate."},
                is_selected=False,
            )
        )
    await session.flush()
    return sorted(suggestions, key=lambda item: item["similarity_score"], reverse=True)


async def get_persisted_candidate_match_suggestions(session: AsyncSession, candidate_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            select(CandidateMatchSuggestion, ProjectMaster)
            .outerjoin(ProjectMaster, ProjectMaster.id == CandidateMatchSuggestion.suggested_project_id)
            .where(CandidateMatchSuggestion.candidate_id == candidate_id)
            .order_by(CandidateMatchSuggestion.score.desc(), CandidateMatchSuggestion.created_at.asc())
        )
    ).all()
    items: list[dict] = []
    for suggestion, project in rows:
        if suggestion.suggested_project_id is None:
            continue
        items.append(
            {
                "project_id": suggestion.suggested_project_id,
                "canonical_name": project.canonical_name if project else "Unknown project",
                "city": project.city if project else None,
                "neighborhood": project.neighborhood if project else None,
                "similarity_score": float(suggestion.score) / 100 if suggestion.score is not None else 0.0,
                "match_state": suggestion.match_state,
                "reasons_json": suggestion.reasons_json or {},
            }
        )
    return items


async def refresh_duplicate_suggestions(session: AsyncSession) -> list[dict]:
    await session.execute(delete(ProjectDuplicateSuggestion).where(ProjectDuplicateSuggestion.review_status == "open"))
    projects = (
        await session.execute(
            select(ProjectMaster)
            .where(ProjectMaster.deleted_at.is_(None), ProjectMaster.merged_into_project_id.is_(None))
            .order_by(ProjectMaster.company_id.asc(), ProjectMaster.canonical_name.asc())
        )
    ).scalars().all()

    items: list[dict] = []
    for index, project in enumerate(projects):
        for other in projects[index + 1 :]:
            if project.company_id != other.company_id:
                continue
            name_score = max(
                similarity_score(project.canonical_name, other.canonical_name),
                *[similarity_score(project.canonical_name, alias) for alias in await _project_alias_names(session, other.id)],
                *[similarity_score(other.canonical_name, alias) for alias in await _project_alias_names(session, project.id)],
            )
            city_match = bool(project.city and other.city and normalize_text(project.city) == normalize_text(other.city))
            neighborhood_match = bool(
                project.neighborhood
                and other.neighborhood
                and normalize_text(project.neighborhood) == normalize_text(other.neighborhood)
            )
            address_overlap = len(
                _address_tokens(await _project_address_texts(session, project.id))
                & _address_tokens(await _project_address_texts(session, other.id))
            )
            weighted = name_score * 0.65 + (0.15 if city_match else 0) + (0.10 if neighborhood_match else 0) + min(0.10, address_overlap * 0.05)
            if weighted < 0.72:
                continue
            match_state = "exact" if weighted >= 0.93 else "likely" if weighted >= 0.82 else "ambiguous"
            suggestion = ProjectDuplicateSuggestion(
                id=uuid4(),
                project_id=project.id,
                duplicate_project_id=other.id,
                match_state=match_state,
                score=Decimal(str(round(weighted * 100, 2))),
                reasons_json={
                    "name_score": round(name_score, 3),
                    "city_match": city_match,
                    "neighborhood_match": neighborhood_match,
                    "address_overlap_count": address_overlap,
                },
                review_status="open",
            )
            session.add(suggestion)
            items.append(
                {
                    "id": suggestion.id,
                    "project_id": project.id,
                    "project_name": project.canonical_name,
                    "duplicate_project_id": other.id,
                    "duplicate_project_name": other.canonical_name,
                    "company_name": "",
                    "city": project.city,
                    "duplicate_city": other.city,
                    "match_state": match_state,
                    "score": suggestion.score,
                    "reasons_json": suggestion.reasons_json or {},
                    "review_status": "open",
                }
            )
    await session.flush()
    return items


async def list_duplicate_suggestions(session: AsyncSession) -> list[dict]:
    duplicate_project = aliased(ProjectMaster)
    existing = (
        await session.execute(
            select(ProjectDuplicateSuggestion, ProjectMaster, Company, duplicate_project)
            .join(ProjectMaster, ProjectMaster.id == ProjectDuplicateSuggestion.project_id)
            .join(Company, Company.id == ProjectMaster.company_id)
            .join(duplicate_project, duplicate_project.id == ProjectDuplicateSuggestion.duplicate_project_id)
        )
    ).all()
    if not existing:
        await refresh_duplicate_suggestions(session)
        existing = (
            await session.execute(
                select(ProjectDuplicateSuggestion, ProjectMaster, Company, duplicate_project)
                .join(ProjectMaster, ProjectMaster.id == ProjectDuplicateSuggestion.project_id)
                .join(Company, Company.id == ProjectMaster.company_id)
                .join(duplicate_project, duplicate_project.id == ProjectDuplicateSuggestion.duplicate_project_id)
            )
        ).all()
    items: list[dict] = []
    for suggestion, project, company, duplicate_project in existing:
        items.append(
            {
                "id": suggestion.id,
                "project_id": project.id,
                "project_name": project.canonical_name,
                "duplicate_project_id": duplicate_project.id,
                "duplicate_project_name": duplicate_project.canonical_name,
                "company_name": company.name_he,
                "city": project.city,
                "duplicate_city": duplicate_project.city,
                "match_state": suggestion.match_state,
                "score": suggestion.score,
                "reasons_json": suggestion.reasons_json or {},
                "review_status": suggestion.review_status,
            }
        )
    return sorted(items, key=lambda item: (item["review_status"] != "open", item["score"]), reverse=True)


async def assess_snapshot_chronology(
    session: AsyncSession,
    project_id: UUID,
    snapshot_date: date,
    report_id: UUID,
    exclude_snapshot_id: UUID | None = None,
) -> tuple[str, str | None]:
    rows = (
        await session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project_id)
            .order_by(ProjectSnapshot.snapshot_date.asc(), ProjectSnapshot.created_at.asc())
        )
    ).scalars().all()
    for snapshot in rows:
        if exclude_snapshot_id and snapshot.id == exclude_snapshot_id:
            continue
        if snapshot.report_id == report_id:
            return "duplicate_date", "Another snapshot already exists for the same report."
        if snapshot.snapshot_date == snapshot_date:
            return "duplicate_date", "Another snapshot already exists on the same date."
        if snapshot.snapshot_date > snapshot_date:
            return "out_of_order", f"Snapshot date is earlier than existing snapshot {snapshot.snapshot_date.isoformat()}."
    return "ok", None


async def get_coverage_dashboard(session: AsyncSession) -> dict:
    companies = (await session.execute(select(Company).order_by(Company.name_he.asc()))).scalars().all()
    reports_registered = int((await session.execute(select(func.count()).select_from(Report))).scalar_one())
    projects_created = int(
        (
            await session.execute(
                select(func.count()).select_from(ProjectMaster).where(ProjectMaster.deleted_at.is_(None))
            )
        ).scalar_one()
    )
    snapshots_created = int((await session.execute(select(func.count()).select_from(ProjectSnapshot))).scalar_one())
    unmatched_candidates = int(
        (
            await session.execute(
                select(func.count())
                .select_from(StagingProjectCandidate)
                .where(StagingProjectCandidate.matching_status == "unmatched")
            )
        ).scalar_one()
    )
    ambiguous_candidates = int(
        (
            await session.execute(
                select(func.count())
                .select_from(StagingProjectCandidate)
                .where(StagingProjectCandidate.matching_status == "ambiguous_match")
            )
        ).scalar_one()
    )
    projects_missing_key_fields = int(
        (
            await session.execute(
                select(func.count())
                .select_from(ProjectMaster)
                .where(
                    ProjectMaster.deleted_at.is_(None),
                    or_(
                        ProjectMaster.city.is_(None),
                        ProjectMaster.project_business_type.is_(None),
                    ),
                )
            )
        ).scalar_one()
    )
    projects_missing_precise_location = int(
        (
            await session.execute(
                select(func.count())
                .select_from(ProjectMaster)
                .where(
                    ProjectMaster.deleted_at.is_(None),
                    ProjectMaster.location_confidence.in_(["city", "unknown"]),
                )
            )
        ).scalar_one()
    )
    company_rows: list[dict] = []
    for company in companies:
        coverage = (
            await session.execute(
                select(CompanyCoverageRegistry).where(CompanyCoverageRegistry.company_id == company.id)
            )
        ).scalar_one_or_none()
        latest_report = None
        if coverage and coverage.latest_report_ingested_id:
            latest_report = (
                await session.execute(select(Report).where(Report.id == coverage.latest_report_ingested_id))
            ).scalar_one_or_none()
        if coverage is None:
            coverage = CompanyCoverageRegistry(company_id=company.id)
            session.add(coverage)
            await session.flush()
        company_rows.append(
            {
                "company_id": company.id,
                "company_name_he": company.name_he,
                "is_in_scope": coverage.is_in_scope,
                "out_of_scope_reason": coverage.out_of_scope_reason,
                "coverage_priority": coverage.coverage_priority,
                "latest_report_ingested_id": coverage.latest_report_ingested_id,
                "latest_report_name": latest_report.filing_reference if latest_report else None,
                "historical_coverage_status": coverage.historical_coverage_status,
                "reports_registered": int(
                    (
                        await session.execute(
                            select(func.count()).select_from(Report).where(Report.company_id == company.id)
                        )
                    ).scalar_one()
                ),
                "projects_created": int(
                    (
                        await session.execute(
                            select(func.count())
                            .select_from(ProjectMaster)
                            .where(ProjectMaster.company_id == company.id, ProjectMaster.deleted_at.is_(None))
                        )
                    ).scalar_one()
                ),
                "snapshots_created": int(
                    (
                        await session.execute(
                            select(func.count())
                            .select_from(ProjectSnapshot)
                            .join(ProjectMaster, ProjectMaster.id == ProjectSnapshot.project_id)
                            .where(ProjectMaster.company_id == company.id)
                        )
                    ).scalar_one()
                ),
                "notes": coverage.notes,
            }
        )
    return {
        "summary": {
            "companies_in_scope": sum(1 for row in company_rows if row["is_in_scope"]),
            "reports_registered": reports_registered,
            "projects_created": projects_created,
            "snapshots_created": snapshots_created,
            "unmatched_candidates": unmatched_candidates,
            "ambiguous_candidates": ambiguous_candidates,
            "projects_missing_key_fields": projects_missing_key_fields,
            "projects_missing_precise_location": projects_missing_precise_location,
        },
        "companies": company_rows,
    }
