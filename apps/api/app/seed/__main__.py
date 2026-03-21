from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import delete

from app.db.session import get_session_factory
from app.models import Company, FieldProvenance, ProjectAddress, ProjectMaster, ProjectSnapshot, Report
from app.seed.data import DATASET_VERSION, NOW, PARSER_VERSION, REAL_DATASET, stable_id


def _confidence_to_score(level: str) -> Decimal:
    return {
        "high": Decimal("95.00"),
        "medium": Decimal("78.00"),
        "low": Decimal("60.00"),
    }[level]


def _origin_for_field(project_data: dict, field_name: str) -> str:
    if field_name in {"canonical_name", "city", "total_units", "marketed_units", "sold_units_cumulative", "unsold_units"}:
        return "reported"
    if field_name in {"project_business_type", "government_program_type", "project_urban_renewal_type"}:
        return "reported" if project_data["classification_confidence"] == "high" else "inferred"
    if field_name in {"project_status", "permit_status"}:
        return "inferred" if project_data.get(field_name) is not None else "unknown"
    return "reported"


def _report_source_metadata(source_file_path: str) -> tuple[bool, str]:
    if "financialreports.eu" in source_file_path:
        return False, "Public filing mirror"
    return True, "Official filing source"


async def seed_real_dataset() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        company_ids = [entry["company"]["id"] for entry in REAL_DATASET]
        report_ids = [entry["report"]["id"] for entry in REAL_DATASET]
        project_ids = [
            stable_id("project", entry["company"]["name_he"], project["slug"])
            for entry in REAL_DATASET
            for project in entry["projects"]
        ]
        snapshot_ids = [
            stable_id("snapshot", entry["company"]["name_he"], project["slug"], str(entry["report"]["period_end_date"]))
            for entry in REAL_DATASET
            for project in entry["projects"]
        ]

        await session.execute(delete(FieldProvenance).where(FieldProvenance.source_report_id.in_(report_ids)))
        await session.execute(delete(ProjectAddress).where(ProjectAddress.project_id.in_(project_ids)))
        await session.execute(delete(ProjectSnapshot).where(ProjectSnapshot.id.in_(snapshot_ids)))
        await session.execute(delete(ProjectMaster).where(ProjectMaster.id.in_(project_ids)))
        await session.execute(delete(Report).where(Report.id.in_(report_ids)))
        await session.execute(delete(Company).where(Company.id.in_(company_ids)))

        for company_entry in REAL_DATASET:
            company_data = company_entry["company"]
            report_data = company_entry["report"]

            session.add(
                Company(
                    id=company_data["id"],
                    name_he=company_data["name_he"],
                    name_en=company_data["name_en"],
                    ticker=company_data["ticker"],
                    public_status="public",
                    sector="residential_developer",
                )
            )
            session.add(
                Report(
                    id=report_data["id"],
                    company_id=company_data["id"],
                    report_type=report_data["report_type"],
                    period_type=report_data["period_type"],
                    period_end_date=report_data["period_end_date"],
                    publish_date=report_data["publish_date"],
                    filing_reference=report_data["filing_reference"],
                    source_url=report_data["source_file_path"],
                    source_file_path=report_data["source_file_path"],
                    source_is_official=_report_source_metadata(report_data["source_file_path"])[0],
                    source_label=_report_source_metadata(report_data["source_file_path"])[1],
                    ingestion_status="published",
                    notes=f"Seeded from curated Phase 2 dataset {DATASET_VERSION}.",
                    parser_version=PARSER_VERSION,
                    status="published",
                )
            )

            for project_data in company_entry["projects"]:
                project_id = stable_id("project", company_data["name_he"], project_data["slug"])
                snapshot_id = stable_id(
                    "snapshot",
                    company_data["name_he"],
                    project_data["slug"],
                    str(report_data["period_end_date"]),
                )
                address_id = stable_id("address", company_data["name_he"], project_data["slug"])
                primary_page = project_data["source_pages"][0] if project_data["source_pages"] else None

                session.add(
                    ProjectMaster(
                        id=project_id,
                        company_id=company_data["id"],
                        canonical_name=project_data["canonical_name"],
                        city=project_data["city"],
                        asset_domain="residential_only",
                        project_business_type=project_data["project_business_type"],
                        government_program_type=project_data["government_program_type"],
                        project_urban_renewal_type=project_data["project_urban_renewal_type"],
                        project_deal_type="ownership",
                        project_usage_profile="residential_only",
                        is_publicly_visible=True,
                        location_confidence="city",
                        classification_confidence=project_data["classification_confidence"],
                        mapping_review_status="approved",
                        source_conflict_flag=False,
                        notes_internal=" | ".join(project_data["notes"]),
                    )
                )
                session.add(
                    ProjectSnapshot(
                        id=snapshot_id,
                        project_id=project_id,
                        report_id=report_data["id"],
                        snapshot_date=report_data["period_end_date"],
                        project_status=project_data["project_status"],
                        permit_status=project_data["permit_status"],
                        total_units=project_data["total_units"],
                        marketed_units=project_data["marketed_units"],
                        sold_units_cumulative=project_data["sold_units_cumulative"],
                        unsold_units=project_data["unsold_units"],
                        needs_admin_review=project_data["classification_confidence"] == "low",
                    )
                )
                session.add(
                    ProjectAddress(
                        id=address_id,
                        project_id=project_id,
                        city=project_data["city"],
                        geometry_type="approximate_area",
                        is_primary=True,
                        location_confidence="city",
                        source_type="imported",
                    )
                )

                core_fields = [
                    ("project_master", project_id, "canonical_name", project_data["canonical_name"], project_data["canonical_name"], "table"),
                    ("project_master", project_id, "city", project_data["city"], project_data["city"], "table"),
                    ("project_master", project_id, "project_business_type", project_data["project_business_type"], project_data["project_business_type"], "table"),
                    ("project_master", project_id, "government_program_type", project_data["government_program_type"], project_data["government_program_type"], "table"),
                    ("project_master", project_id, "project_urban_renewal_type", project_data["project_urban_renewal_type"], project_data["project_urban_renewal_type"], "table"),
                    ("snapshot", snapshot_id, "total_units", str(project_data["total_units"]), str(project_data["total_units"]), "table"),
                    ("snapshot", snapshot_id, "marketed_units", str(project_data["marketed_units"]), str(project_data["marketed_units"]), "table"),
                    ("snapshot", snapshot_id, "sold_units_cumulative", None if project_data["sold_units_cumulative"] is None else str(project_data["sold_units_cumulative"]), None if project_data["sold_units_cumulative"] is None else str(project_data["sold_units_cumulative"]), "table"),
                    ("snapshot", snapshot_id, "unsold_units", None if project_data["unsold_units"] is None else str(project_data["unsold_units"]), None if project_data["unsold_units"] is None else str(project_data["unsold_units"]), "table"),
                    ("snapshot", snapshot_id, "project_status", project_data["project_status"], project_data["project_status"], "text"),
                    ("snapshot", snapshot_id, "permit_status", project_data["permit_status"], project_data["permit_status"], "text"),
                ]

                for entity_type, entity_id, field_name, raw_value, normalized_value, extraction_method in core_fields:
                    session.add(
                        FieldProvenance(
                            id=stable_id("provenance", company_data["name_he"], project_data["slug"], entity_type, field_name),
                            entity_type=entity_type,
                            entity_id=entity_id,
                            field_name=field_name,
                            raw_value=raw_value,
                            normalized_value=normalized_value,
                            source_report_id=report_data["id"],
                            source_page=primary_page,
                            source_section=project_data["source_section"],
                            extraction_method=extraction_method,
                            parser_version=PARSER_VERSION,
                            confidence_score=_confidence_to_score(project_data["classification_confidence"]),
                            value_origin_type=_origin_for_field(project_data, field_name),
                            review_status="approved",
                            reviewed_at=NOW,
                            created_at=NOW,
                        )
                    )

                for missing_field in project_data["missing_fields"]:
                    note = next((item for item in project_data["notes"] if "left null" in item or missing_field.split("_")[0] in item), "Left null intentionally because the source report does not disclose this field.")
                    session.add(
                        FieldProvenance(
                            id=stable_id("provenance-missing", company_data["name_he"], project_data["slug"], missing_field),
                            entity_type="snapshot",
                            entity_id=snapshot_id,
                            field_name=missing_field,
                            raw_value=None,
                            normalized_value=None,
                            source_report_id=report_data["id"],
                            source_page=primary_page,
                            source_section=note,
                            extraction_method="text",
                            parser_version=PARSER_VERSION,
                            confidence_score=Decimal("40.00"),
                            value_origin_type="unknown",
                            review_status="approved",
                            reviewed_at=NOW,
                            created_at=NOW,
                        )
                    )

        await session.commit()

    print(f"Seeded curated real dataset {DATASET_VERSION}.")


if __name__ == "__main__":
    asyncio.run(seed_real_dataset())
