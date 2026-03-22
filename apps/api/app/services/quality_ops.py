from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Company,
    ParserRunLog,
    ProjectAddress,
    ProjectMaster,
    ProjectSnapshot,
    Report,
    ReviewQueueItem,
    StagingProjectCandidate,
)
from app.services.identity_ops import get_coverage_dashboard
from app.services.parser_pipeline import get_parser_health_summary


LOCATION_RANK = {
    "unknown": 0,
    "city_only": 1,
    "approximate": 2,
    "exact": 3,
}


def _decimal_to_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _severity_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


async def list_admin_anomalies(session: AsyncSession) -> list[dict]:
    anomalies: list[dict] = []
    project_rows = (
        await session.execute(
            select(ProjectMaster, Company)
            .join(Company, Company.id == ProjectMaster.company_id)
            .where(ProjectMaster.deleted_at.is_(None))
            .order_by(Company.name_he.asc(), ProjectMaster.canonical_name.asc())
        )
    ).all()

    latest_reports = {}
    for company_id, report_id, filing_reference, period_end_date in (
        await session.execute(
            select(Report.company_id, Report.id, Report.filing_reference, Report.period_end_date)
            .order_by(Report.company_id.asc(), Report.period_end_date.desc(), Report.publish_date.desc().nullslast())
        )
    ).all():
        latest_reports.setdefault(
            company_id,
            {
                "report_id": report_id,
                "report_name": filing_reference,
                "period_end_date": period_end_date,
            },
        )

    for project, company in project_rows:
        snapshots = (
            await session.execute(
                select(ProjectSnapshot)
                .where(ProjectSnapshot.project_id == project.id)
                .order_by(ProjectSnapshot.snapshot_date.desc(), ProjectSnapshot.created_at.desc())
            )
        ).scalars().all()
        latest_snapshot = snapshots[0] if snapshots else None

        if latest_snapshot is not None:
            if (
                latest_snapshot.sold_units_cumulative is not None
                and latest_snapshot.marketed_units is not None
                and latest_snapshot.sold_units_cumulative > latest_snapshot.marketed_units
            ):
                anomalies.append(
                    {
                        "id": f"sold_gt_marketed:{latest_snapshot.id}",
                        "anomaly_type": "sold_gt_marketed",
                        "severity": "high",
                        "project_id": project.id,
                        "project_name": project.canonical_name,
                        "company_name": company.name_he,
                        "snapshot_id": latest_snapshot.id,
                        "report_id": latest_snapshot.report_id,
                        "source_report_name": next(
                            (latest_reports[company.id]["report_name"] for _ in [0] if company.id in latest_reports),
                            None,
                        ),
                        "summary": "Sold units exceed marketed units in the latest snapshot.",
                        "details_json": {
                            "sold_units_cumulative": latest_snapshot.sold_units_cumulative,
                            "marketed_units": latest_snapshot.marketed_units,
                            "snapshot_date": latest_snapshot.snapshot_date.isoformat(),
                        },
                    }
                )

            if latest_snapshot.unsold_units is not None and latest_snapshot.unsold_units < 0:
                anomalies.append(
                    {
                        "id": f"negative_unsold:{latest_snapshot.id}",
                        "anomaly_type": "negative_unsold",
                        "severity": "high",
                        "project_id": project.id,
                        "project_name": project.canonical_name,
                        "company_name": company.name_he,
                        "snapshot_id": latest_snapshot.id,
                        "report_id": latest_snapshot.report_id,
                        "source_report_name": latest_reports.get(company.id, {}).get("report_name"),
                        "summary": "Unsold units are negative in the latest snapshot.",
                        "details_json": {
                            "unsold_units": latest_snapshot.unsold_units,
                            "snapshot_date": latest_snapshot.snapshot_date.isoformat(),
                        },
                    }
                )

            if (
                latest_snapshot.total_units is not None
                and latest_snapshot.marketed_units is not None
                and latest_snapshot.total_units < latest_snapshot.marketed_units
            ):
                anomalies.append(
                    {
                        "id": f"total_lt_marketed:{latest_snapshot.id}",
                        "anomaly_type": "total_lt_marketed",
                        "severity": "high",
                        "project_id": project.id,
                        "project_name": project.canonical_name,
                        "company_name": company.name_he,
                        "snapshot_id": latest_snapshot.id,
                        "report_id": latest_snapshot.report_id,
                        "source_report_name": latest_reports.get(company.id, {}).get("report_name"),
                        "summary": "Total units are lower than marketed units in the latest snapshot.",
                        "details_json": {
                            "total_units": latest_snapshot.total_units,
                            "marketed_units": latest_snapshot.marketed_units,
                            "snapshot_date": latest_snapshot.snapshot_date.isoformat(),
                        },
                    }
                )

            if (
                latest_snapshot.gross_margin_expected_pct is not None
                and (
                    latest_snapshot.gross_margin_expected_pct < Decimal("0")
                    or latest_snapshot.gross_margin_expected_pct > Decimal("60")
                )
            ):
                anomalies.append(
                    {
                        "id": f"unrealistic_margin:{latest_snapshot.id}",
                        "anomaly_type": "unrealistic_margin",
                        "severity": "medium",
                        "project_id": project.id,
                        "project_name": project.canonical_name,
                        "company_name": company.name_he,
                        "snapshot_id": latest_snapshot.id,
                        "report_id": latest_snapshot.report_id,
                        "source_report_name": latest_reports.get(company.id, {}).get("report_name"),
                        "summary": "Gross margin is outside the expected review band.",
                        "details_json": {
                            "gross_margin_expected_pct": _decimal_to_string(latest_snapshot.gross_margin_expected_pct),
                            "snapshot_date": latest_snapshot.snapshot_date.isoformat(),
                        },
                    }
                )

            if latest_snapshot.chronology_status != "ok":
                anomalies.append(
                    {
                        "id": f"snapshot_chronology:{latest_snapshot.id}",
                        "anomaly_type": "snapshot_chronology_conflict",
                        "severity": "high",
                        "project_id": project.id,
                        "project_name": project.canonical_name,
                        "company_name": company.name_he,
                        "snapshot_id": latest_snapshot.id,
                        "report_id": latest_snapshot.report_id,
                        "source_report_name": latest_reports.get(company.id, {}).get("report_name"),
                        "summary": "Snapshot chronology requires review.",
                        "details_json": {
                            "chronology_status": latest_snapshot.chronology_status,
                            "chronology_notes": latest_snapshot.chronology_notes,
                            "snapshot_date": latest_snapshot.snapshot_date.isoformat(),
                        },
                    }
                )

        latest_company_report = latest_reports.get(company.id)
        if latest_company_report and snapshots:
            has_latest_cycle = any(snapshot.report_id == latest_company_report["report_id"] for snapshot in snapshots)
            if not has_latest_cycle:
                anomalies.append(
                    {
                        "id": f"missing_latest_cycle:{project.id}:{latest_company_report['report_id']}",
                        "anomaly_type": "missing_latest_cycle",
                        "severity": "medium",
                        "project_id": project.id,
                        "project_name": project.canonical_name,
                        "company_name": company.name_he,
                        "snapshot_id": None,
                        "report_id": latest_company_report["report_id"],
                        "source_report_name": latest_company_report["report_name"],
                        "summary": "Project has historical snapshots but is missing the latest company report cycle.",
                        "details_json": {
                            "latest_company_period_end": latest_company_report["period_end_date"].isoformat(),
                            "known_snapshot_count": len(snapshots),
                        },
                    }
                )

        addresses = (
            await session.execute(
                select(ProjectAddress).where(ProjectAddress.project_id == project.id).order_by(ProjectAddress.is_primary.desc())
            )
        ).scalars().all()
        best_address_confidence = max((LOCATION_RANK.get(address.location_confidence, 0) for address in addresses), default=0)
        if best_address_confidence > LOCATION_RANK.get(project.location_confidence, 0):
            anomalies.append(
                {
                    "id": f"location_confidence_downgrade:{project.id}",
                    "anomaly_type": "location_confidence_downgrade",
                    "severity": "medium",
                    "project_id": project.id,
                    "project_name": project.canonical_name,
                    "company_name": company.name_he,
                    "snapshot_id": None,
                    "report_id": None,
                    "source_report_name": None,
                    "summary": "Project-level location confidence is lower than the best linked address.",
                    "details_json": {
                        "project_location_confidence": project.location_confidence,
                        "best_address_confidence": next(
                            (
                                address.location_confidence
                                for address in addresses
                                if LOCATION_RANK.get(address.location_confidence, 0) == best_address_confidence
                            ),
                            None,
                        ),
                        "address_count": len(addresses),
                    },
                }
            )

    anomalies.sort(key=lambda item: (_severity_rank(item["severity"]), item["project_name"]), reverse=True)
    return anomalies


async def get_admin_ops_dashboard(session: AsyncSession) -> dict:
    coverage = await get_coverage_dashboard(session)
    parser_health = await get_parser_health_summary(session)
    anomalies = await list_admin_anomalies(session)

    ingestion_status_rows = (
        await session.execute(
            select(Report.ingestion_status, func.count()).group_by(Report.ingestion_status)
        )
    ).all()
    ingestion_health = {status: int(count) for status, count in ingestion_status_rows}

    matching_backlog = {
        "unmatched": int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(StagingProjectCandidate)
                    .where(StagingProjectCandidate.matching_status == "unmatched")
                )
            ).scalar_one()
        ),
        "ambiguous": int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(StagingProjectCandidate)
                    .where(StagingProjectCandidate.matching_status == "ambiguous_match")
                )
            ).scalar_one()
        ),
        "open_review_items": int(
            (
                await session.execute(
                    select(func.count()).select_from(ReviewQueueItem).where(ReviewQueueItem.status == "open")
                )
            ).scalar_one()
        ),
    }

    publish_backlog = {
        "ready_to_publish": int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(StagingProjectCandidate)
                    .where(
                        StagingProjectCandidate.matching_status.in_(["matched_existing_project", "new_project_needed"]),
                        StagingProjectCandidate.publish_status != "published",
                    )
                )
            ).scalar_one()
        ),
        "draft_candidates": int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(StagingProjectCandidate)
                    .where(StagingProjectCandidate.publish_status == "draft")
                )
            ).scalar_one()
        ),
    }

    location_rows = (
        await session.execute(
            select(ProjectMaster.location_confidence, func.count())
            .where(ProjectMaster.deleted_at.is_(None))
            .group_by(ProjectMaster.location_confidence)
        )
    ).all()
    location_completeness = {
        "breakdown": {confidence: int(count) for confidence, count in location_rows},
        "projects_with_precise_location": sum(
            int(count) for confidence, count in location_rows if confidence in {"exact", "approximate"}
        ),
    }

    latest_registered_report_period = (
        await session.execute(select(func.max(Report.period_end_date)))
    ).scalar_one_or_none()

    return {
        "summary": {
            "reports_registered": coverage["summary"]["reports_registered"],
            "projects_created": coverage["summary"]["projects_created"],
            "snapshots_created": coverage["summary"]["snapshots_created"],
            "open_anomalies": len(anomalies),
            "parser_failed_runs": parser_health["failed_runs"],
            "ready_to_publish": publish_backlog["ready_to_publish"],
        },
        "ingestion_health": {
            "by_status": ingestion_health,
            "latest_registered_report_period": latest_registered_report_period,
        },
        "matching_backlog": matching_backlog,
        "publish_backlog": publish_backlog,
        "coverage_completeness": coverage["summary"],
        "location_completeness": location_completeness,
        "parser_health": parser_health,
        "top_anomalies": anomalies[:12],
    }
