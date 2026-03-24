from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import or_, select

from app.db.session import get_session_factory
from app.models import Company, Report
from app.services.ingestion import create_admin_report, get_admin_report_qa, update_admin_report
from app.services.parser_pipeline import run_report_extraction


@dataclass(frozen=True, slots=True)
class PilotSource:
    source_file_path: str
    company_name_he: str
    company_name_en: str | None
    ticker: str | None
    report_name: str
    report_type: str
    period_type: str
    period_end_date: date
    published_at: date | None
    source_label: str
    source_is_official: bool
    notes: str
    include_in_pilot: bool
    skip_reason: str | None = None


PILOT_SOURCES = (
    PilotSource(
        source_file_path=r"C:\Users\simis\Downloads\P1729852-00.pdf",
        company_name_he="אאורה",
        company_name_en="Aura Investments Ltd",
        ticker="AURA",
        report_name="דוח תקופתי לשנת 2025",
        report_type="annual",
        period_type="annual",
        period_end_date=date(2025, 12, 31),
        published_at=None,
        source_label="Pilot annual report PDF (uploaded file)",
        source_is_official=False,
        notes="Pilot ingestion from uploaded annual report PDF only. Published date stayed null because it was not verified outside the file.",
        include_in_pilot=True,
    ),
    PilotSource(
        source_file_path=r"C:\Users\simis\Downloads\1729842.pdf",
        company_name_he='מגידו י.ק. בע"מ',
        company_name_en="Megido Y.K. Ltd",
        ticker=None,
        report_name="דוח תקופתי לשנת 2025",
        report_type="annual",
        period_type="annual",
        period_end_date=date(2025, 12, 31),
        published_at=date(2026, 3, 22),
        source_label="Pilot annual report PDF (uploaded file)",
        source_is_official=False,
        notes="Pilot ingestion from uploaded annual report PDF only. Company metadata inferred from the uploaded report itself.",
        include_in_pilot=True,
    ),
    PilotSource(
        source_file_path=r"C:\Users\simis\Downloads\1729794.pdf",
        company_name_he="הכשרה התחדשות",
        company_name_en=None,
        ticker=None,
        report_name="מצגת שוק שנתית 2025",
        report_type="presentation",
        period_type="interim",
        period_end_date=date(2025, 12, 31),
        published_at=None,
        source_label="Uploaded presentation PDF",
        source_is_official=False,
        notes="Skipped from the annual-report pilot because the file is a presentation, not an annual report.",
        include_in_pilot=False,
        skip_reason="presentation_not_annual_report",
    ),
)


async def _resolve_company(session, source: PilotSource) -> Company:
    filters = [Company.name_he == source.company_name_he]
    if source.ticker:
        filters.append(Company.ticker == source.ticker)
    company = (
        await session.execute(select(Company).where(or_(*filters)).order_by(Company.created_at.asc()))
    ).scalar_one_or_none()
    if company is not None:
        return company

    company = Company(
        id=uuid5(NAMESPACE_URL, f"pilot-company:{source.company_name_he}"),
        name_he=source.company_name_he,
        name_en=source.company_name_en,
        ticker=source.ticker,
        public_status="public",
        sector="residential_developer",
    )
    session.add(company)
    await session.commit()
    return company


async def _upsert_report(session, source: PilotSource) -> Report:
    company = await _resolve_company(session, source)
    report = (
        await session.execute(
            select(Report)
            .where(Report.source_file_path == source.source_file_path)
            .order_by(Report.created_at.asc())
        )
    ).scalar_one_or_none()

    payload = {
        "company_id": str(company.id),
        "report_name": source.report_name,
        "report_type": source.report_type,
        "period_type": source.period_type,
        "period_end_date": source.period_end_date,
        "published_at": source.published_at,
        "source_url": None,
        "source_file_path": source.source_file_path,
        "source_is_official": source.source_is_official,
        "source_label": source.source_label,
        "ingestion_status": "ready_for_staging",
        "notes": source.notes,
    }

    if report is None:
        created = await create_admin_report(session, payload)
        report = (
            await session.execute(select(Report).where(Report.id == created["id"]))
        ).scalar_one()
    else:
        await update_admin_report(session, report.id, payload)
        report = (
            await session.execute(select(Report).where(Report.id == report.id))
        ).scalar_one()
    return report


async def run_pilot(*, extract: bool, print_qa: bool) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        print("Pilot annual report ingestion")
        print("=============================")
        for source in PILOT_SOURCES:
            if not Path(source.source_file_path).exists():
                print(f"missing_file path={source.source_file_path}")
                continue

            if not source.include_in_pilot:
                print(f"skipped path={source.source_file_path} reason={source.skip_reason}")
                continue

            report = await _upsert_report(session, source)
            print(
                f"registered report_id={report.id} company={source.company_name_he} period_end={source.period_end_date.isoformat()} path={source.source_file_path}"
            )
            if extract:
                await run_report_extraction(session, report.id)
                print(f"extracted report_id={report.id}")

            if print_qa:
                qa = await get_admin_report_qa(session, report.id)
                if qa is None:
                    print(f"qa_unavailable report_id={report.id}")
                    continue
                print(
                    "qa"
                    f" report_id={report.id}"
                    f" total_candidates={qa['summary']['total_candidates']}"
                    f" matched_existing={qa['summary']['matched_existing_projects']}"
                    f" new_needed={qa['summary']['new_projects_needed']}"
                    f" ambiguous={qa['summary']['ambiguous_candidates']}"
                    f" missing_key_fields={qa['summary']['missing_key_field_total']}"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Register and extract the uploaded annual-report pilot PDFs.")
    parser.add_argument("--no-extract", action="store_true", help="Register reports but do not run extraction.")
    parser.add_argument("--no-qa", action="store_true", help="Skip QA summary output.")
    args = parser.parse_args()
    asyncio.run(run_pilot(extract=not args.no_extract, print_qa=not args.no_qa))


if __name__ == "__main__":
    main()
