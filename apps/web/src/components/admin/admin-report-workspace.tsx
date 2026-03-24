"use client";

import type {
  AdminAddressCandidate,
  AdminCandidateDetail,
  AdminCandidateSummary,
  AdminFieldCandidate,
  AdminParserRun,
  AdminReportQa,
  AdminReportDetail,
} from "@real-estat-map/shared";
import {
  CONFIDENCE_LEVELS,
  GOVERNMENT_PROGRAM_TYPES,
  LOCATION_CONFIDENCE_LEVELS,
  PERMIT_STATUSES,
  PROJECT_BUSINESS_TYPES,
  PROJECT_DISCLOSURE_LEVELS,
  PROJECT_LIFECYCLE_STAGES,
  PROJECT_STATUSES,
  REPORT_INGESTION_STATUSES,
  SOURCE_SECTION_KINDS,
  STAGING_PUBLISH_STATUSES,
  URBAN_RENEWAL_TYPES,
  VALUE_ORIGIN_TYPES,
} from "@real-estat-map/shared";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";

import {
  createAdminCandidate,
  getAdminCandidateDetail,
  getAdminReportDetail,
  getAdminReportParserRuns,
  getAdminReportQa,
  matchAdminCandidate,
  publishAdminCandidate,
  runAdminReportExtraction,
  updateAdminCandidate,
  updateAdminReport,
} from "@/lib/api";
import {
  formatAddressLabel,
  formatCurrency,
  formatDate,
  formatDisclosureLevelLabel,
  formatLifecycleStageLabel,
  formatNumber,
  formatPercent,
  formatSectionKindLabel,
} from "@/lib/format";

const REPORT_TYPES = ["annual", "q1", "q2", "q3", "prospectus", "presentation"];
const PERIOD_TYPES = ["annual", "quarterly", "interim"];
const REVIEW_STATUSES = ["pending", "approved", "rejected"];
const STAGING_REVIEW_STATUSES = ["pending", "approved", "rejected"];

type ReportFormState = {
  report_name: string;
  report_type: string;
  period_type: string;
  period_end_date: string;
  published_at: string;
  source_url: string;
  source_file_path: string;
  source_is_official: boolean;
  source_label: string;
  ingestion_status: string;
  notes: string;
  staging_publish_status: string;
  staging_review_status: string;
  staging_notes_internal: string;
};

type CandidateCreateState = {
  candidate_project_name: string;
  city: string;
  neighborhood: string;
  candidate_lifecycle_stage: string;
  candidate_disclosure_level: string;
  candidate_section_kind: string;
  candidate_materiality_flag: boolean;
  source_table_name: string;
  source_row_label: string;
  extraction_profile_key: string;
  project_business_type: string;
  government_program_type: string;
  project_urban_renewal_type: string;
  project_status: string;
  permit_status: string;
  total_units: string;
  marketed_units: string;
  sold_units_cumulative: string;
  unsold_units: string;
  avg_price_per_sqm_cumulative: string;
  gross_profit_total_expected: string;
  gross_margin_expected_pct: string;
  location_confidence: string;
  value_origin_type: string;
  confidence_level: string;
  review_status: string;
  review_notes: string;
};

type CandidateFormState = CandidateCreateState & {
  matched_project_id: string;
};

type FieldDraft = {
  id?: string;
  field_name: string;
  raw_value: string;
  normalized_value: string;
  source_page: string;
  source_section: string;
  source_table_name: string;
  source_row_label: string;
  extraction_profile_key: string;
  value_origin_type: string;
  confidence_level: string;
  review_status: string;
  review_notes: string;
};

type AddressDraft = {
  id?: string;
  address_text_raw: string;
  street: string;
  house_number_from: string;
  house_number_to: string;
  city: string;
  lat: string;
  lng: string;
  location_confidence: string;
  is_primary: boolean;
  value_origin_type: string;
  confidence_level: string;
  review_status: string;
  review_notes: string;
};

function buildReportForm(report: AdminReportDetail): ReportFormState {
  return {
    report_name: report.reportName ?? "",
    report_type: report.reportType,
    period_type: report.periodType,
    period_end_date: report.periodEndDate,
    published_at: report.publishedAt ?? "",
    source_url: report.sourceUrl ?? "",
    source_file_path: report.sourceFilePath ?? "",
    source_is_official: report.sourceIsOfficial,
    source_label: report.sourceLabel ?? "",
    ingestion_status: report.ingestionStatus,
    notes: report.notes ?? "",
    staging_publish_status: report.stagingPublishStatus,
    staging_review_status: report.stagingReviewStatus,
    staging_notes_internal: report.stagingNotesInternal ?? "",
  };
}

function emptyCandidateCreateState(): CandidateCreateState {
  return {
    candidate_project_name: "",
    city: "",
    neighborhood: "",
    candidate_lifecycle_stage: "",
    candidate_disclosure_level: "",
    candidate_section_kind: "",
    candidate_materiality_flag: false,
    source_table_name: "",
    source_row_label: "",
    extraction_profile_key: "",
    project_business_type: "regular_dev",
    government_program_type: "none",
    project_urban_renewal_type: "none",
    project_status: "",
    permit_status: "",
    total_units: "",
    marketed_units: "",
    sold_units_cumulative: "",
    unsold_units: "",
    avg_price_per_sqm_cumulative: "",
    gross_profit_total_expected: "",
    gross_margin_expected_pct: "",
    location_confidence: "city_only",
    value_origin_type: "manual",
    confidence_level: "medium",
    review_status: "pending",
    review_notes: "",
  };
}

function buildCandidateForm(candidate: AdminCandidateDetail): CandidateFormState {
  return {
    candidate_project_name: candidate.candidateProjectName,
    city: candidate.city ?? "",
    neighborhood: candidate.neighborhood ?? "",
    candidate_lifecycle_stage: candidate.candidateLifecycleStage ?? "",
    candidate_disclosure_level: candidate.candidateDisclosureLevel ?? "",
    candidate_section_kind: candidate.candidateSectionKind ?? "",
    candidate_materiality_flag: candidate.candidateMaterialityFlag ?? false,
    source_table_name: candidate.sourceTableName ?? "",
    source_row_label: candidate.sourceRowLabel ?? "",
    extraction_profile_key: candidate.extractionProfileKey ?? "",
    project_business_type: candidate.projectBusinessType ?? "regular_dev",
    government_program_type: candidate.governmentProgramType,
    project_urban_renewal_type: candidate.projectUrbanRenewalType,
    project_status: candidate.projectStatus ?? "",
    permit_status: candidate.permitStatus ?? "",
    total_units: candidate.totalUnits?.toString() ?? "",
    marketed_units: candidate.marketedUnits?.toString() ?? "",
    sold_units_cumulative: candidate.soldUnitsCumulative?.toString() ?? "",
    unsold_units: candidate.unsoldUnits?.toString() ?? "",
    avg_price_per_sqm_cumulative: candidate.avgPricePerSqmCumulative?.toString() ?? "",
    gross_profit_total_expected: candidate.grossProfitTotalExpected?.toString() ?? "",
    gross_margin_expected_pct: candidate.grossMarginExpectedPct?.toString() ?? "",
    location_confidence: candidate.locationConfidence,
    value_origin_type: candidate.valueOriginType,
    confidence_level: candidate.confidenceLevel,
    review_status: candidate.reviewStatus,
    review_notes: candidate.reviewNotes ?? "",
    matched_project_id: candidate.matchedProjectId ?? "",
  };
}

function buildFieldDraft(item: AdminFieldCandidate): FieldDraft {
  return {
    id: item.id,
    field_name: item.fieldName,
    raw_value: item.rawValue ?? "",
    normalized_value: item.normalizedValue ?? "",
    source_page: item.sourcePage?.toString() ?? "",
    source_section: item.sourceSection ?? "",
    source_table_name: item.sourceTableName ?? "",
    source_row_label: item.sourceRowLabel ?? "",
    extraction_profile_key: item.extractionProfileKey ?? "",
    value_origin_type: item.valueOriginType,
    confidence_level: item.confidenceLevel,
    review_status: item.reviewStatus,
    review_notes: item.reviewNotes ?? "",
  };
}

function buildAddressDraft(item: AdminAddressCandidate): AddressDraft {
  return {
    id: item.id,
    address_text_raw: item.addressTextRaw ?? "",
    street: item.street ?? "",
    house_number_from: item.houseNumberFrom?.toString() ?? "",
    house_number_to: item.houseNumberTo?.toString() ?? "",
    city: item.city ?? "",
    lat: item.lat?.toString() ?? "",
    lng: item.lng?.toString() ?? "",
    location_confidence: item.locationConfidence,
    is_primary: item.isPrimary,
    value_origin_type: item.valueOriginType,
    confidence_level: item.confidenceLevel,
    review_status: item.reviewStatus,
    review_notes: item.reviewNotes ?? "",
  };
}

function emptyFieldDraft(): FieldDraft {
  return {
    field_name: "",
    raw_value: "",
    normalized_value: "",
    source_page: "",
    source_section: "",
    source_table_name: "",
    source_row_label: "",
    extraction_profile_key: "",
    value_origin_type: "manual",
    confidence_level: "medium",
    review_status: "pending",
    review_notes: "",
  };
}

function emptyAddressDraft(city = ""): AddressDraft {
  return {
    address_text_raw: "",
    street: "",
    house_number_from: "",
    house_number_to: "",
    city,
    lat: "",
    lng: "",
    location_confidence: city ? "city_only" : "unknown",
    is_primary: false,
    value_origin_type: "manual",
    confidence_level: "medium",
    review_status: "pending",
    review_notes: "",
  };
}

function toNullableNumber(value: string) {
  if (!value.trim()) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeCandidateByBusinessType<T extends CandidateCreateState | CandidateFormState>(form: T): T {
  if (form.project_business_type !== "govt_program") {
    form.government_program_type = "none";
  }
  if (form.project_business_type !== "urban_renewal") {
    form.project_urban_renewal_type = "none";
  }
  return form;
}

function buildCandidatePayload(form: CandidateCreateState | CandidateFormState, fieldDrafts: FieldDraft[], addressDrafts: AddressDraft[]) {
  const normalized = normalizeCandidateByBusinessType({ ...form });

  return {
    candidate_project_name: normalized.candidate_project_name,
    city: normalized.city || null,
    neighborhood: normalized.neighborhood || null,
    candidate_lifecycle_stage: normalized.candidate_lifecycle_stage || null,
    candidate_disclosure_level: normalized.candidate_disclosure_level || null,
    candidate_section_kind: normalized.candidate_section_kind || null,
    candidate_materiality_flag: normalized.candidate_materiality_flag,
    source_table_name: normalized.source_table_name || null,
    source_row_label: normalized.source_row_label || null,
    extraction_profile_key: normalized.extraction_profile_key || null,
    project_business_type: normalized.project_business_type || null,
    government_program_type: normalized.government_program_type,
    project_urban_renewal_type: normalized.project_urban_renewal_type,
    project_status: normalized.project_status || null,
    permit_status: normalized.permit_status || null,
    total_units: toNullableNumber(normalized.total_units),
    marketed_units: toNullableNumber(normalized.marketed_units),
    sold_units_cumulative: toNullableNumber(normalized.sold_units_cumulative),
    unsold_units: toNullableNumber(normalized.unsold_units),
    avg_price_per_sqm_cumulative: toNullableNumber(normalized.avg_price_per_sqm_cumulative),
    gross_profit_total_expected: toNullableNumber(normalized.gross_profit_total_expected),
    gross_margin_expected_pct: toNullableNumber(normalized.gross_margin_expected_pct),
    location_confidence: normalized.location_confidence,
    value_origin_type: normalized.value_origin_type,
    confidence_level: normalized.confidence_level,
    review_status: normalized.review_status,
    review_notes: normalized.review_notes || null,
    matched_project_id: "matched_project_id" in normalized ? normalized.matched_project_id || null : undefined,
    field_candidates: fieldDrafts
      .filter((item) => item.field_name.trim())
      .map((item) => ({
        id: item.id,
        field_name: item.field_name,
        raw_value: item.raw_value || null,
        normalized_value: item.normalized_value || null,
        source_page: toNullableNumber(item.source_page),
        source_section: item.source_section || null,
        source_table_name: item.source_table_name || null,
        source_row_label: item.source_row_label || null,
        extraction_profile_key: item.extraction_profile_key || null,
        value_origin_type: item.value_origin_type,
        confidence_level: item.confidence_level,
        review_status: item.review_status,
        review_notes: item.review_notes || null,
      })),
    address_candidates: addressDrafts
      .filter((item) => item.city.trim() || item.address_text_raw.trim() || item.street.trim())
      .map((item) => ({
        id: item.id,
        address_text_raw: item.address_text_raw || null,
        street: item.street || null,
        house_number_from: toNullableNumber(item.house_number_from),
        house_number_to: toNullableNumber(item.house_number_to),
        city: item.city || null,
        lat: toNullableNumber(item.lat),
        lng: toNullableNumber(item.lng),
        location_confidence: item.location_confidence,
        is_primary: item.is_primary,
        value_origin_type: item.value_origin_type,
        confidence_level: item.confidence_level,
        review_status: item.review_status,
        review_notes: item.review_notes || null,
      })),
  };
}

function matchTone(value: string) {
  if (["published", "approved", "matched_existing_project"].includes(value)) {
    return "accent";
  }
  if (["ambiguous_match", "rejected"].includes(value)) {
    return "warning";
  }
  return "default";
}

function tagClassName(value: string) {
  const tone = matchTone(value);
  if (tone === "accent") {
    return "tag tag-accent";
  }
  if (tone === "warning") {
    return "tag tag-warning";
  }
  return "tag";
}

function CandidateQueueItem({
  isActive,
  item,
  onSelect,
  reportId,
}: {
  isActive: boolean;
  item: AdminCandidateSummary;
  onSelect: (candidateId: string) => void;
  reportId: string;
}) {
  return (
    <div className={`candidate-queue-card${isActive ? " candidate-queue-card-active" : ""}`}>
      <div className="candidate-queue-header">
        <div>
          <strong>{item.candidateProjectName}</strong>
          <p className="panel-copy">
            {[item.city, item.neighborhood].filter(Boolean).join(" | ") || "Location not disclosed yet"}
          </p>
        </div>
        <div className="tag-row">
          <span className={tagClassName(item.matchingStatus)}>{item.matchingStatus}</span>
          <span className={tagClassName(item.publishStatus)}>{item.publishStatus}</span>
        </div>
      </div>
      <div className="candidate-queue-meta">
        <span>confidence {item.confidenceLevel}</span>
        <span>review {item.reviewStatus}</span>
        <span>{item.candidateLifecycleStage ? formatLifecycleStageLabel(item.candidateLifecycleStage) : "Lifecycle n/a"}</span>
        <span>{item.candidateDisclosureLevel ? formatDisclosureLevelLabel(item.candidateDisclosureLevel) : "Disclosure n/a"}</span>
        <span>{item.matchedProjectName ?? "Unmatched"}</span>
      </div>
      <div className="form-actions">
        <button className="secondary-button" onClick={() => onSelect(item.id)} type="button">
          Open in workspace
        </button>
        <Link className="inline-link" href={`/admin/sources/${reportId}?candidate=${item.id}`}>
          Deep link
        </Link>
      </div>
    </div>
  );
}

export function AdminReportWorkspace({
  initialReport,
  initialCandidateId,
}: {
  initialReport: AdminReportDetail;
  initialCandidateId: string | null;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [report, setReport] = useState(initialReport);
  const [reportForm, setReportForm] = useState<ReportFormState>(() => buildReportForm(initialReport));
  const [candidateCreateForm, setCandidateCreateForm] = useState<CandidateCreateState>(() => emptyCandidateCreateState());
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(
    initialCandidateId ?? initialReport.candidates[0]?.id ?? null,
  );
  const [candidate, setCandidate] = useState<AdminCandidateDetail | null>(null);
  const [candidateForm, setCandidateForm] = useState<CandidateFormState | null>(null);
  const [fieldDrafts, setFieldDrafts] = useState<FieldDraft[]>([]);
  const [addressDrafts, setAddressDrafts] = useState<AddressDraft[]>([]);
  const [reportFeedback, setReportFeedback] = useState<string | null>(null);
  const [candidateFeedback, setCandidateFeedback] = useState<string | null>(null);
  const [candidateError, setCandidateError] = useState<string | null>(null);
  const [parserRuns, setParserRuns] = useState<AdminParserRun[]>([]);
  const [reportQa, setReportQa] = useState<AdminReportQa | null>(null);
  const [parserFeedback, setParserFeedback] = useState<string | null>(null);
  const [isCandidateLoading, setIsCandidateLoading] = useState(false);
  const [isPending, startTransition] = useTransition();

  const candidateCountLabel = useMemo(
    () => `${report.candidates.length} candidate${report.candidates.length === 1 ? "" : "s"}`,
    [report.candidates.length],
  );

  useEffect(() => {
    const candidateFromUrl = searchParams.get("candidate");
    if (candidateFromUrl && candidateFromUrl !== selectedCandidateId) {
      setSelectedCandidateId(candidateFromUrl);
      return;
    }

    if (!candidateFromUrl && !selectedCandidateId && report.candidates[0]?.id) {
      setSelectedCandidateId(report.candidates[0].id);
    }
  }, [report.candidates, searchParams, selectedCandidateId]);

  useEffect(() => {
    if (!selectedCandidateId) {
      setCandidate(null);
      setCandidateForm(null);
      setFieldDrafts([]);
      setAddressDrafts([]);
      setCandidateError(null);
      return;
    }

    let isCancelled = false;
    const candidateId = selectedCandidateId;

    async function loadCandidate() {
      setIsCandidateLoading(true);
      setCandidateError(null);
      const result = await getAdminCandidateDetail(candidateId);
      if (isCancelled) {
        return;
      }

      if (!result.item) {
        setCandidate(null);
        setCandidateForm(null);
        setFieldDrafts([]);
        setAddressDrafts([]);
        setCandidateError("Candidate details are temporarily unavailable.");
      } else {
        setCandidate(result.item);
        setCandidateForm(buildCandidateForm(result.item));
        setFieldDrafts(result.item.fieldCandidates.map(buildFieldDraft));
        setAddressDrafts(
          result.item.addressCandidates.length > 0
            ? result.item.addressCandidates.map(buildAddressDraft)
            : [emptyAddressDraft(result.item.city ?? "")],
        );
      }

      setIsCandidateLoading(false);
    }

    void loadCandidate();

    return () => {
      isCancelled = true;
    };
  }, [selectedCandidateId]);

  function syncReport(nextReport: AdminReportDetail) {
    setReport(nextReport);
    setReportForm(buildReportForm(nextReport));
  }

  async function refreshParserRuns() {
    const result = await getAdminReportParserRuns(report.id);
    if (result.state === "error") {
      setParserFeedback("Parser run history is temporarily unavailable.");
      return;
    }
    setParserRuns(result.items);
  }

  async function refreshReportQa() {
    const result = await getAdminReportQa(report.id);
    if (result.item) {
      setReportQa(result.item);
    }
  }

  function syncCandidate(nextCandidate: AdminCandidateDetail) {
    setCandidate(nextCandidate);
    setCandidateForm(buildCandidateForm(nextCandidate));
    setFieldDrafts(nextCandidate.fieldCandidates.map(buildFieldDraft));
    setAddressDrafts(
      nextCandidate.addressCandidates.length > 0
        ? nextCandidate.addressCandidates.map(buildAddressDraft)
        : [emptyAddressDraft(nextCandidate.city ?? "")],
    );
  }

  function setCandidateQuery(candidateId: string | null) {
    const nextSearchParams = new URLSearchParams(searchParams.toString());
    if (candidateId) {
      nextSearchParams.set("candidate", candidateId);
    } else {
      nextSearchParams.delete("candidate");
    }
    const nextQuery = nextSearchParams.toString();
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    setSelectedCandidateId(candidateId);
  }

  async function refreshReport(preferredCandidateId?: string | null) {
    const result = await getAdminReportDetail(report.id);
    if (result.item) {
      syncReport(result.item);
      await refreshParserRuns();
      await refreshReportQa();
      if (preferredCandidateId) {
        setCandidateQuery(preferredCandidateId);
      } else if (!selectedCandidateId && result.item.candidates[0]?.id) {
        setCandidateQuery(result.item.candidates[0].id);
      }
    }
  }

  useEffect(() => {
    void refreshParserRuns();
    void refreshReportQa();
  }, [report.id]);

  function handleSaveReport() {
    startTransition(async () => {
      setReportFeedback(null);
      const result = await updateAdminReport(report.id, {
        report_name: reportForm.report_name,
        report_type: reportForm.report_type,
        period_type: reportForm.period_type,
        period_end_date: reportForm.period_end_date,
        published_at: reportForm.published_at || null,
        source_url: reportForm.source_url || null,
        source_file_path: reportForm.source_file_path || null,
        source_is_official: reportForm.source_is_official,
        source_label: reportForm.source_label || null,
        ingestion_status: reportForm.ingestion_status,
        notes: reportForm.notes || null,
        staging_publish_status: reportForm.staging_publish_status,
        staging_review_status: reportForm.staging_review_status,
        staging_notes_internal: reportForm.staging_notes_internal || null,
      });

      if (!result.item) {
        setReportFeedback("Could not save report metadata.");
        return;
      }

      syncReport(result.item);
      setReportFeedback("Report metadata saved.");
    });
  }

  function handleCreateCandidate() {
    startTransition(async () => {
      setCandidateFeedback(null);
      const result = await createAdminCandidate(report.id, buildCandidatePayload(candidateCreateForm, [], []));

      if (!result.item) {
        setCandidateFeedback("Could not create staging candidate.");
        return;
      }

      syncCandidate(result.item);
      setCandidateCreateForm(emptyCandidateCreateState());
      setCandidateFeedback("Staging candidate created.");
      await refreshReport(result.item.id);
    });
  }

  function handleRunExtraction() {
    startTransition(async () => {
      setParserFeedback(null);
      const result = await runAdminReportExtraction(report.id);
      if (!result.item) {
        setParserFeedback("Could not run automated extraction for this source.");
        await refreshParserRuns();
        return;
      }
      syncReport(result.item);
      await refreshParserRuns();
      await refreshReportQa();
      setParserFeedback("Automated extraction completed. Review the parser-created candidates before publish.");
    });
  }

  function handleSaveCandidate() {
    if (!candidate || !candidateForm) {
      return;
    }

    startTransition(async () => {
      setCandidateFeedback(null);
      const result = await updateAdminCandidate(candidate.id, buildCandidatePayload(candidateForm, fieldDrafts, addressDrafts));

      if (!result.item) {
        setCandidateFeedback("Could not save candidate changes.");
        return;
      }

      syncCandidate(result.item);
      setCandidateFeedback("Candidate saved.");
      await refreshReport(result.item.id);
    });
  }

  function handleMatch(matchStatus: string, matchedProjectId?: string) {
    if (!candidate || !candidateForm) {
      return;
    }

    startTransition(async () => {
      setCandidateFeedback(null);
      const resolvedMatchedProjectId =
        matchStatus === "matched_existing_project"
          ? ((matchedProjectId ?? candidateForm.matched_project_id) || null)
          : null;
      const result = await matchAdminCandidate(candidate.id, {
        match_status: matchStatus,
        matched_project_id: resolvedMatchedProjectId,
        reviewer_note: candidateForm.review_notes || null,
      });

      if (!result.item) {
        setCandidateFeedback("Could not save matching decision.");
        return;
      }

      syncCandidate(result.item);
      setCandidateFeedback(`Matching decision saved: ${matchStatus}.`);
      await refreshReport(result.item.id);
    });
  }

  function handlePublishCandidate() {
    if (!candidate || !candidateForm) {
      return;
    }

    startTransition(async () => {
      setCandidateFeedback(null);
      const result = await publishAdminCandidate(candidate.id, {
        reviewer_note: candidateForm.review_notes || null,
      });

      if (!result.item) {
        setCandidateFeedback("Could not publish candidate.");
        return;
      }

      syncCandidate(result.item);
      setCandidateFeedback("Candidate published into canonical tables.");
      await refreshReport(result.item.id);
    });
  }

  return (
    <div className="section-stack">
      <div className="admin-form-card section-stack">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Report Registry</p>
            <h2>{report.reportName ?? "Unnamed report"}</h2>
            <p className="panel-copy">
              {report.companyNameHe} | period end {formatDate(report.periodEndDate)} | {candidateCountLabel}
            </p>
          </div>
          <div className="tag-row">
            <span className={tagClassName(report.ingestionStatus)}>{report.ingestionStatus}</span>
            <span className={tagClassName(report.stagingPublishStatus)}>{report.stagingPublishStatus}</span>
            <span className={report.sourceIsOfficial ? "tag tag-accent" : "tag tag-warning"}>
              {report.sourceIsOfficial ? "official source" : "unverified source"}
            </span>
          </div>
        </div>

        {reportFeedback ? <p className="muted-copy">{reportFeedback}</p> : null}

        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Report name</span>
            <input value={reportForm.report_name} onChange={(event) => setReportForm((current) => ({ ...current, report_name: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Report type</span>
            <select value={reportForm.report_type} onChange={(event) => setReportForm((current) => ({ ...current, report_type: event.target.value }))}>
              {REPORT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Period type</span>
            <select value={reportForm.period_type} onChange={(event) => setReportForm((current) => ({ ...current, period_type: event.target.value }))}>
              {PERIOD_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Period end date</span>
            <input type="date" value={reportForm.period_end_date} onChange={(event) => setReportForm((current) => ({ ...current, period_end_date: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Published at</span>
            <input type="date" value={reportForm.published_at} onChange={(event) => setReportForm((current) => ({ ...current, published_at: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Source URL</span>
            <input value={reportForm.source_url} onChange={(event) => setReportForm((current) => ({ ...current, source_url: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Source file path / storage ref</span>
            <input value={reportForm.source_file_path} onChange={(event) => setReportForm((current) => ({ ...current, source_file_path: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Source label</span>
            <input value={reportForm.source_label} onChange={(event) => setReportForm((current) => ({ ...current, source_label: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Ingestion status</span>
            <select value={reportForm.ingestion_status} onChange={(event) => setReportForm((current) => ({ ...current, ingestion_status: event.target.value }))}>
              {REPORT_INGESTION_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Staging publish status</span>
            <select value={reportForm.staging_publish_status} onChange={(event) => setReportForm((current) => ({ ...current, staging_publish_status: event.target.value }))}>
              {STAGING_PUBLISH_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Staging review status</span>
            <select value={reportForm.staging_review_status} onChange={(event) => setReportForm((current) => ({ ...current, staging_review_status: event.target.value }))}>
              {STAGING_REVIEW_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="panel-copy">
            <input checked={reportForm.source_is_official} type="checkbox" onChange={(event) => setReportForm((current) => ({ ...current, source_is_official: event.target.checked }))} />{" "}
            Source is official
          </label>
          <label className="filter-field">
            <span>Report note</span>
            <textarea value={reportForm.notes} onChange={(event) => setReportForm((current) => ({ ...current, notes: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Staging internal note</span>
            <textarea value={reportForm.staging_notes_internal} onChange={(event) => setReportForm((current) => ({ ...current, staging_notes_internal: event.target.value }))} />
          </label>
        </div>

        <div className="form-actions">
          <button className="primary-button" disabled={isPending || !reportForm.report_name || !reportForm.period_end_date} onClick={handleSaveReport} type="button">
            Save report metadata
          </button>
          <button
            className="secondary-button"
            disabled={isPending || (!reportForm.source_url && !reportForm.source_file_path)}
            onClick={handleRunExtraction}
            type="button"
          >
            Run automated extraction
          </button>
        </div>

        {parserFeedback ? <p className="muted-copy">{parserFeedback}</p> : null}

        <div className="admin-form-card section-stack">
          <div>
            <p className="eyebrow">Parser Runs</p>
            <h3>Extraction diagnostics</h3>
            <p className="panel-copy">
              Automated extraction writes into staging only. Every parser-created candidate still has to move through intake review, matching, and publish.
            </p>
          </div>

          {parserRuns.length > 0 ? (
            <div className="section-stack">
              {parserRuns.map((run) => (
                <div className="candidate-suggestion-card" key={run.id}>
                  <div className="candidate-queue-header">
                    <div>
                      <strong>{run.status}</strong>
                      <p className="panel-copy">
                        parser {run.parserVersion} | started {formatDate(run.startedAt)} | finished {formatDate(run.finishedAt)}
                      </p>
                    </div>
                    <div className="tag-row">
                      <span className="tag">{run.sectionsFound} sections</span>
                      <span className="tag">{run.candidateCount} candidates</span>
                      <span className="tag">{run.fieldCandidateCount} fields</span>
                    </div>
                  </div>
                  <p className="muted-copy">
                    {run.sourceReference ?? "No source reference recorded"}
                  </p>
                  {run.warnings.length > 0 ? <p className="muted-copy">Warnings: {run.warnings.join(" | ")}</p> : null}
                  {run.errors.length > 0 ? <p className="muted-copy">Errors: {run.errors.join(" | ")}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No parser runs yet.</strong>
              <p className="panel-copy">Save a valid source URL or file path, then run extraction to generate staging candidates automatically.</p>
            </div>
          )}
        </div>

        <div className="admin-form-card section-stack">
          <div>
            <p className="eyebrow">Pilot QA</p>
            <h3>Report-level extraction review</h3>
            <p className="panel-copy">
              Compare the report families that were detected against the candidate set currently waiting in staging.
            </p>
          </div>

          {reportQa ? (
            <>
              <div className="stats-grid">
                <div>
                  <strong>{reportQa.summary.totalCandidates}</strong>
                  <span>Candidates created</span>
                </div>
                <div>
                  <strong>{reportQa.summary.projectsDetected}</strong>
                  <span>Projects detected</span>
                </div>
                <div>
                  <strong>{reportQa.summary.matchedExistingProjects}</strong>
                  <span>Matched existing</span>
                </div>
                <div>
                  <strong>{reportQa.summary.newProjectsNeeded}</strong>
                  <span>New projects needed</span>
                </div>
                <div>
                  <strong>{reportQa.summary.ambiguousCandidates}</strong>
                  <span>Ambiguous</span>
                </div>
                <div>
                  <strong>{reportQa.summary.missingKeyFieldTotal}</strong>
                  <span>Missing key fields</span>
                </div>
              </div>

              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Disclosure family</th>
                      <th>Sections found</th>
                      <th>Candidates</th>
                      <th>Matched existing</th>
                      <th>New project</th>
                      <th>Ambiguous</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportQa.familyCoverage.map((item) => (
                      <tr key={item.sectionKind}>
                        <td>{formatSectionKindLabel(item.sectionKind)}</td>
                        <td>{item.sectionCount}</td>
                        <td>{item.candidateCount}</td>
                        <td>{item.matchedExistingCount}</td>
                        <td>{item.newProjectCount}</td>
                        <td>{item.ambiguousCount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="section-stack">
                <p className="panel-copy">
                  <strong>Lifecycle:</strong>{" "}
                  {reportQa.lifecycleStageDistribution.length > 0
                    ? reportQa.lifecycleStageDistribution
                        .map((item) => `${formatLifecycleStageLabel(item.key)} (${item.count})`)
                        .join(" | ")
                    : "No lifecycle stages detected yet."}
                </p>
                <p className="panel-copy">
                  <strong>Disclosure depth:</strong>{" "}
                  {reportQa.disclosureLevelDistribution.length > 0
                    ? reportQa.disclosureLevelDistribution
                        .map((item) => `${formatDisclosureLevelLabel(item.key)} (${item.count})`)
                        .join(" | ")
                    : "No disclosure levels detected yet."}
                </p>
              </div>

              {reportQa.missingKeyFields.length > 0 ? (
                <div className="tag-row">
                  {reportQa.missingKeyFields.slice(0, 12).map((item) => (
                    <span className="tag" key={item.fieldName}>
                      {item.fieldName}: {item.missingCount}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <strong>No key-field gaps detected.</strong>
                  <p className="panel-copy">The current staging set already covers the pilot fields tracked by this QA summary.</p>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <strong>No QA summary yet.</strong>
              <p className="panel-copy">Run extraction or create report candidates to populate the pilot QA dashboard.</p>
            </div>
          )}
        </div>
      </div>

      <div className="report-workspace-grid">
        <div className="section-stack">
          <div className="admin-form-card section-stack">
            <div>
              <p className="eyebrow">New Candidate</p>
              <h3>Create staging project candidate</h3>
              <p className="panel-copy">
                Start with the project-level summary from the report. Field rows, addresses, matching, and publish review continue in the workspace.
              </p>
            </div>

            <div className="admin-form-grid">
              <label className="filter-field">
                <span>Candidate project name</span>
                <input
                  value={candidateCreateForm.candidate_project_name}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, candidate_project_name: event.target.value }))}
                />
              </label>
              <label className="filter-field">
                <span>City</span>
                <input value={candidateCreateForm.city} onChange={(event) => setCandidateCreateForm((current) => ({ ...current, city: event.target.value }))} />
              </label>
              <label className="filter-field">
                <span>Neighborhood</span>
                <input
                  value={candidateCreateForm.neighborhood}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, neighborhood: event.target.value }))}
                />
              </label>
              <label className="filter-field">
                <span>Lifecycle stage</span>
                <select
                  value={candidateCreateForm.candidate_lifecycle_stage}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, candidate_lifecycle_stage: event.target.value }))}
                >
                  <option value="">Not set</option>
                  {PROJECT_LIFECYCLE_STAGES.map((value) => (
                    <option key={value} value={value}>
                      {formatLifecycleStageLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Disclosure level</span>
                <select
                  value={candidateCreateForm.candidate_disclosure_level}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, candidate_disclosure_level: event.target.value }))}
                >
                  <option value="">Not set</option>
                  {PROJECT_DISCLOSURE_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {formatDisclosureLevelLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Section kind</span>
                <select
                  value={candidateCreateForm.candidate_section_kind}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, candidate_section_kind: event.target.value }))}
                >
                  <option value="">Not set</option>
                  {SOURCE_SECTION_KINDS.map((value) => (
                    <option key={value} value={value}>
                      {formatSectionKindLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Business type</span>
                <select
                  value={candidateCreateForm.project_business_type}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, project_business_type: event.target.value }))}
                >
                  {PROJECT_BUSINESS_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Project status</span>
                <select value={candidateCreateForm.project_status} onChange={(event) => setCandidateCreateForm((current) => ({ ...current, project_status: event.target.value }))}>
                  <option value="">Not disclosed</option>
                  {PROJECT_STATUSES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Permit status</span>
                <select value={candidateCreateForm.permit_status} onChange={(event) => setCandidateCreateForm((current) => ({ ...current, permit_status: event.target.value }))}>
                  <option value="">Not disclosed</option>
                  {PERMIT_STATUSES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Total units</span>
                <input value={candidateCreateForm.total_units} onChange={(event) => setCandidateCreateForm((current) => ({ ...current, total_units: event.target.value }))} />
              </label>
              <label className="filter-field">
                <span>Marketed units</span>
                <input value={candidateCreateForm.marketed_units} onChange={(event) => setCandidateCreateForm((current) => ({ ...current, marketed_units: event.target.value }))} />
              </label>
              <label className="filter-field">
                <span>Sold units cumulative</span>
                <input value={candidateCreateForm.sold_units_cumulative} onChange={(event) => setCandidateCreateForm((current) => ({ ...current, sold_units_cumulative: event.target.value }))} />
              </label>
              <label className="filter-field">
                <span>Location confidence</span>
                <select
                  value={candidateCreateForm.location_confidence}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, location_confidence: event.target.value }))}
                >
                  {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Value origin</span>
                <select
                  value={candidateCreateForm.value_origin_type}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, value_origin_type: event.target.value }))}
                >
                  {VALUE_ORIGIN_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Confidence</span>
                <select
                  value={candidateCreateForm.confidence_level}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, confidence_level: event.target.value }))}
                >
                  {CONFIDENCE_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Extraction profile key</span>
                <input
                  value={candidateCreateForm.extraction_profile_key}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, extraction_profile_key: event.target.value }))}
                />
              </label>
              <label className="filter-field">
                <span>Source table name</span>
                <input
                  value={candidateCreateForm.source_table_name}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, source_table_name: event.target.value }))}
                />
              </label>
              <label className="filter-field">
                <span>Source row label</span>
                <input
                  value={candidateCreateForm.source_row_label}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, source_row_label: event.target.value }))}
                />
              </label>
              <label className="filter-field">
                <span>Reviewer note</span>
                <textarea
                  value={candidateCreateForm.review_notes}
                  onChange={(event) => setCandidateCreateForm((current) => ({ ...current, review_notes: event.target.value }))}
                />
              </label>
            </div>

            <label className="panel-copy">
              <input
                checked={candidateCreateForm.candidate_materiality_flag}
                type="checkbox"
                onChange={(event) => setCandidateCreateForm((current) => ({ ...current, candidate_materiality_flag: event.target.checked }))}
              />{" "}
              Mark as material-project style disclosure
            </label>

            <div className="form-actions">
              <button
                className="primary-button"
                disabled={isPending || !candidateCreateForm.candidate_project_name}
                onClick={handleCreateCandidate}
                type="button"
              >
                Create staging candidate
              </button>
            </div>
          </div>

          <div className="admin-form-card section-stack">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Candidates</p>
                <h3>Staging candidates for this report</h3>
              </div>
              <div className="tag-row">
                <span className="tag">{candidateCountLabel}</span>
              </div>
            </div>

            {report.candidates.length > 0 ? (
              <div className="candidate-queue">
                {report.candidates.map((item) => (
                  <CandidateQueueItem
                    isActive={item.id === selectedCandidateId}
                    item={item}
                    key={item.id}
                    onSelect={setCandidateQuery}
                    reportId={report.id}
                  />
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <strong>No staging candidates yet.</strong>
                <p className="panel-copy">Create the first candidate from the report data above to begin matching and review.</p>
              </div>
            )}
          </div>
        </div>

        <div className="section-stack">
          {candidateFeedback ? <p className="muted-copy">{candidateFeedback}</p> : null}

          {isCandidateLoading ? (
            <div className="admin-form-card">
              <p className="panel-copy">Loading candidate detail...</p>
            </div>
          ) : null}

          {!isCandidateLoading && candidateError ? (
            <div className="empty-state">
              <strong>Candidate detail is unavailable.</strong>
              <p className="panel-copy">{candidateError}</p>
            </div>
          ) : null}

          {!isCandidateLoading && !candidate && !candidateError ? (
            <div className="empty-state">
              <strong>Select a candidate to review.</strong>
              <p className="panel-copy">The queue on the left is the staging layer. Canonical tables only change after publish.</p>
            </div>
          ) : null}

          {candidate && candidateForm ? (
            <>
              <div className="admin-form-card section-stack">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Candidate Review</p>
                    <h3>{candidate.candidateProjectName}</h3>
                    <p className="panel-copy">
                      {candidate.companyNameHe} | matched {candidate.matchedProjectName ?? "not yet"} | updated {formatDate(candidate.updatedAt)}
                    </p>
                  </div>
                  <div className="tag-row">
                    <span className={tagClassName(candidate.matchingStatus)}>{candidate.matchingStatus}</span>
                    <span className={tagClassName(candidate.publishStatus)}>{candidate.publishStatus}</span>
                    <span className="tag">{candidate.confidenceLevel}</span>
                    {candidate.candidateLifecycleStage ? <span className="tag">{formatLifecycleStageLabel(candidate.candidateLifecycleStage)}</span> : null}
                    {candidate.candidateDisclosureLevel ? (
                      <span className="tag tag-accent">{formatDisclosureLevelLabel(candidate.candidateDisclosureLevel)}</span>
                    ) : null}
                    {candidate.candidateSectionKind ? <span className="tag">{formatSectionKindLabel(candidate.candidateSectionKind)}</span> : null}
                  </div>
                </div>

                <div className="admin-form-grid">
                  <label className="filter-field">
                    <span>Candidate project name</span>
                    <input
                      value={candidateForm.candidate_project_name}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, candidate_project_name: event.target.value } : current))}
                    />
                  </label>
                  <label className="filter-field">
                    <span>City</span>
                    <input value={candidateForm.city} onChange={(event) => setCandidateForm((current) => (current ? { ...current, city: event.target.value } : current))} />
                  </label>
                  <label className="filter-field">
                    <span>Neighborhood</span>
                    <input
                      value={candidateForm.neighborhood}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, neighborhood: event.target.value } : current))}
                    />
                  </label>
                  <label className="filter-field">
                    <span>Lifecycle stage</span>
                    <select
                      value={candidateForm.candidate_lifecycle_stage}
                      onChange={(event) =>
                        setCandidateForm((current) => (current ? { ...current, candidate_lifecycle_stage: event.target.value } : current))
                      }
                    >
                      <option value="">Not set</option>
                      {PROJECT_LIFECYCLE_STAGES.map((value) => (
                        <option key={value} value={value}>
                          {formatLifecycleStageLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Disclosure level</span>
                    <select
                      value={candidateForm.candidate_disclosure_level}
                      onChange={(event) =>
                        setCandidateForm((current) => (current ? { ...current, candidate_disclosure_level: event.target.value } : current))
                      }
                    >
                      <option value="">Not set</option>
                      {PROJECT_DISCLOSURE_LEVELS.map((value) => (
                        <option key={value} value={value}>
                          {formatDisclosureLevelLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Section kind</span>
                    <select
                      value={candidateForm.candidate_section_kind}
                      onChange={(event) =>
                        setCandidateForm((current) => (current ? { ...current, candidate_section_kind: event.target.value } : current))
                      }
                    >
                      <option value="">Not set</option>
                      {SOURCE_SECTION_KINDS.map((value) => (
                        <option key={value} value={value}>
                          {formatSectionKindLabel(value)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Business type</span>
                    <select
                      value={candidateForm.project_business_type}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, project_business_type: event.target.value } : current))}
                    >
                      {PROJECT_BUSINESS_TYPES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Government program type</span>
                    <select
                      value={candidateForm.government_program_type}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, government_program_type: event.target.value } : current))}
                    >
                      {GOVERNMENT_PROGRAM_TYPES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Urban renewal type</span>
                    <select
                      value={candidateForm.project_urban_renewal_type}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, project_urban_renewal_type: event.target.value } : current))}
                    >
                      {URBAN_RENEWAL_TYPES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Project status</span>
                    <select value={candidateForm.project_status} onChange={(event) => setCandidateForm((current) => (current ? { ...current, project_status: event.target.value } : current))}>
                      <option value="">Not disclosed</option>
                      {PROJECT_STATUSES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Permit status</span>
                    <select value={candidateForm.permit_status} onChange={(event) => setCandidateForm((current) => (current ? { ...current, permit_status: event.target.value } : current))}>
                      <option value="">Not disclosed</option>
                      {PERMIT_STATUSES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Location confidence</span>
                    <select
                      value={candidateForm.location_confidence}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, location_confidence: event.target.value } : current))}
                    >
                      {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Value origin</span>
                    <select
                      value={candidateForm.value_origin_type}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, value_origin_type: event.target.value } : current))}
                    >
                      {VALUE_ORIGIN_TYPES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Confidence</span>
                    <select
                      value={candidateForm.confidence_level}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, confidence_level: event.target.value } : current))}
                    >
                      {CONFIDENCE_LEVELS.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Extraction profile key</span>
                    <input
                      value={candidateForm.extraction_profile_key}
                      onChange={(event) =>
                        setCandidateForm((current) => (current ? { ...current, extraction_profile_key: event.target.value } : current))
                      }
                    />
                  </label>
                  <label className="filter-field">
                    <span>Source table name</span>
                    <input
                      value={candidateForm.source_table_name}
                      onChange={(event) =>
                        setCandidateForm((current) => (current ? { ...current, source_table_name: event.target.value } : current))
                      }
                    />
                  </label>
                  <label className="filter-field">
                    <span>Source row label</span>
                    <input
                      value={candidateForm.source_row_label}
                      onChange={(event) =>
                        setCandidateForm((current) => (current ? { ...current, source_row_label: event.target.value } : current))
                      }
                    />
                  </label>
                  <label className="filter-field">
                    <span>Review status</span>
                    <select
                      value={candidateForm.review_status}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, review_status: event.target.value } : current))}
                    >
                      {REVIEW_STATUSES.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="filter-field">
                    <span>Total units</span>
                    <input value={candidateForm.total_units} onChange={(event) => setCandidateForm((current) => (current ? { ...current, total_units: event.target.value } : current))} />
                  </label>
                  <label className="filter-field">
                    <span>Marketed units</span>
                    <input value={candidateForm.marketed_units} onChange={(event) => setCandidateForm((current) => (current ? { ...current, marketed_units: event.target.value } : current))} />
                  </label>
                  <label className="filter-field">
                    <span>Sold units cumulative</span>
                    <input value={candidateForm.sold_units_cumulative} onChange={(event) => setCandidateForm((current) => (current ? { ...current, sold_units_cumulative: event.target.value } : current))} />
                  </label>
                  <label className="filter-field">
                    <span>Unsold units</span>
                    <input value={candidateForm.unsold_units} onChange={(event) => setCandidateForm((current) => (current ? { ...current, unsold_units: event.target.value } : current))} />
                  </label>
                  <label className="filter-field">
                    <span>Avg price per sqm</span>
                    <input
                      value={candidateForm.avg_price_per_sqm_cumulative}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, avg_price_per_sqm_cumulative: event.target.value } : current))}
                    />
                  </label>
                  <label className="filter-field">
                    <span>Gross profit expected</span>
                    <input
                      value={candidateForm.gross_profit_total_expected}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, gross_profit_total_expected: event.target.value } : current))}
                    />
                  </label>
                  <label className="filter-field">
                    <span>Gross margin pct</span>
                    <input
                      value={candidateForm.gross_margin_expected_pct}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, gross_margin_expected_pct: event.target.value } : current))}
                    />
                  </label>
                  <label className="filter-field">
                    <span>Matched canonical project ID</span>
                    <input
                      value={candidateForm.matched_project_id}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, matched_project_id: event.target.value } : current))}
                    />
                  </label>
                  <label className="filter-field">
                    <span>Reviewer note</span>
                    <textarea
                      value={candidateForm.review_notes}
                      onChange={(event) => setCandidateForm((current) => (current ? { ...current, review_notes: event.target.value } : current))}
                    />
                  </label>
                </div>

                <label className="panel-copy">
                  <input
                    checked={candidateForm.candidate_materiality_flag}
                    type="checkbox"
                    onChange={(event) =>
                      setCandidateForm((current) => (current ? { ...current, candidate_materiality_flag: event.target.checked } : current))
                    }
                  />{" "}
                  Material-project style disclosure
                </label>

                <div className="form-actions">
                  <button className="primary-button" disabled={isPending} onClick={handleSaveCandidate} type="button">
                    Save staging candidate
                  </button>
                </div>
              </div>

              <div className="admin-form-card section-stack">
                <div>
                  <p className="eyebrow">Field Candidates</p>
                  <h3>Field-level source rows</h3>
                </div>

                {fieldDrafts.length > 0 ? (
                  <div className="section-stack">
                    {fieldDrafts.map((draft, index) => (
                      <div className="address-card section-stack" key={`${draft.id ?? "new"}-${index}`}>
                        <div className="candidate-inline-grid">
                          <input placeholder="Field name" value={draft.field_name} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, field_name: event.target.value } : item)))} />
                          <input placeholder="Raw value" value={draft.raw_value} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, raw_value: event.target.value } : item)))} />
                          <input placeholder="Normalized value" value={draft.normalized_value} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, normalized_value: event.target.value } : item)))} />
                          <input placeholder="Source page" value={draft.source_page} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, source_page: event.target.value } : item)))} />
                          <input placeholder="Source section" value={draft.source_section} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, source_section: event.target.value } : item)))} />
                          <input placeholder="Source table" value={draft.source_table_name} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, source_table_name: event.target.value } : item)))} />
                          <input placeholder="Source row label" value={draft.source_row_label} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, source_row_label: event.target.value } : item)))} />
                          <input placeholder="Extraction profile key" value={draft.extraction_profile_key} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, extraction_profile_key: event.target.value } : item)))} />
                          <select value={draft.value_origin_type} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, value_origin_type: event.target.value } : item)))}>
                            {VALUE_ORIGIN_TYPES.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                          <select value={draft.confidence_level} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, confidence_level: event.target.value } : item)))}>
                            {CONFIDENCE_LEVELS.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                          <select value={draft.review_status} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, review_status: event.target.value } : item)))}>
                            {REVIEW_STATUSES.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                          <textarea placeholder="Reviewer note" value={draft.review_notes} onChange={(event) => setFieldDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, review_notes: event.target.value } : item)))} />
                        </div>
                        <div className="form-actions">
                          <button className="secondary-button" onClick={() => setFieldDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index))} type="button">
                            Remove field row
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <strong>No field rows yet.</strong>
                    <p className="panel-copy">Add source-backed field rows before publish if you want field-level provenance detail.</p>
                  </div>
                )}

                <div className="form-actions">
                  <button className="secondary-button" onClick={() => setFieldDrafts((current) => [...current, emptyFieldDraft()])} type="button">
                    Add field row
                  </button>
                </div>
              </div>

              <div className="admin-form-card section-stack">
                <div>
                  <p className="eyebrow">Address Candidates</p>
                  <h3>Address staging rows</h3>
                </div>
                {addressDrafts.length > 0 ? (
                  <div className="section-stack">
                    {addressDrafts.map((draft, index) => (
                      <div className="address-card section-stack" key={`${draft.id ?? "new"}-${index}`}>
                        <strong>{formatAddressLabel({ addressTextRaw: draft.address_text_raw, street: draft.street, city: draft.city })}</strong>
                        <div className="candidate-inline-grid">
                          <input placeholder="Raw address text" value={draft.address_text_raw} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, address_text_raw: event.target.value } : item)))} />
                          <input placeholder="Street" value={draft.street} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, street: event.target.value } : item)))} />
                          <input placeholder="House number from" value={draft.house_number_from} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, house_number_from: event.target.value } : item)))} />
                          <input placeholder="House number to" value={draft.house_number_to} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, house_number_to: event.target.value } : item)))} />
                          <input placeholder="City" value={draft.city} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, city: event.target.value } : item)))} />
                          <input placeholder="Latitude" value={draft.lat} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, lat: event.target.value } : item)))} />
                          <input placeholder="Longitude" value={draft.lng} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, lng: event.target.value } : item)))} />
                          <select value={draft.location_confidence} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, location_confidence: event.target.value } : item)))}>
                            {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                          <select value={draft.value_origin_type} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, value_origin_type: event.target.value } : item)))}>
                            {VALUE_ORIGIN_TYPES.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                          <select value={draft.confidence_level} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, confidence_level: event.target.value } : item)))}>
                            {CONFIDENCE_LEVELS.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                          <select value={draft.review_status} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, review_status: event.target.value } : item)))}>
                            {REVIEW_STATUSES.map((value) => (
                              <option key={value} value={value}>
                                {value}
                              </option>
                            ))}
                          </select>
                          <label className="panel-copy">
                            <input
                              checked={draft.is_primary}
                              type="checkbox"
                              onChange={(event) =>
                                setAddressDrafts((current) =>
                                  current.map((item, itemIndex) =>
                                    itemIndex === index ? { ...item, is_primary: event.target.checked } : { ...item, is_primary: false },
                                  ),
                                )
                              }
                            />{" "}
                            Primary address
                          </label>
                          <textarea placeholder="Reviewer note" value={draft.review_notes} onChange={(event) => setAddressDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, review_notes: event.target.value } : item)))} />
                        </div>
                        <div className="form-actions">
                          <button className="secondary-button" onClick={() => setAddressDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index))} type="button">
                            Remove address row
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <strong>No address candidates yet.</strong>
                    <p className="panel-copy">Keep city-only entries if the report does not disclose a precise address.</p>
                  </div>
                )}

                <div className="form-actions">
                  <button className="secondary-button" onClick={() => setAddressDrafts((current) => [...current, emptyAddressDraft(candidate.city ?? "")])} type="button">
                    Add address row
                  </button>
                </div>
              </div>

              <div className="admin-form-card section-stack">
                <div>
                  <p className="eyebrow">Matching</p>
                  <h3>Canonical project decision</h3>
                </div>

                {candidate.matchSuggestions.length > 0 ? (
                  <div className="section-stack">
                    {candidate.matchSuggestions.map((suggestion) => (
                      <div className="candidate-suggestion-card" key={suggestion.projectId}>
                        <div>
                          <strong>{suggestion.canonicalName}</strong>
                          <p className="panel-copy">
                            {[suggestion.city, suggestion.neighborhood].filter(Boolean).join(" | ") || "No location detail"}
                          </p>
                          <p className="panel-copy">
                            {suggestion.matchState} | similarity {suggestion.similarityScore.toFixed(2)}
                          </p>
                          {Object.keys(suggestion.reasonsJson).length > 0 ? (
                            <p className="muted-copy">
                              {Object.entries(suggestion.reasonsJson)
                                .slice(0, 4)
                                .map(([key, value]) => `${key}: ${String(value)}`)
                                .join(" | ")}
                            </p>
                          ) : null}
                        </div>
                        <div className="form-actions">
                          <Link className="inline-link" href={`/admin/projects/${suggestion.projectId}`}>
                            Open project
                          </Link>
                          <button className="secondary-button" onClick={() => setCandidateForm((current) => (current ? { ...current, matched_project_id: suggestion.projectId } : current))} type="button">
                            Fill match ID
                          </button>
                          <button className="primary-button" disabled={isPending} onClick={() => handleMatch("matched_existing_project", suggestion.projectId)} type="button">
                            Match to this project
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <strong>No automatic suggestions.</strong>
                    <p className="panel-copy">You can still link manually by canonical project ID, mark as new project needed, or leave ambiguous.</p>
                  </div>
                )}

                <div className="form-actions">
                  <button className="secondary-button" disabled={isPending || !candidateForm.matched_project_id} onClick={() => handleMatch("matched_existing_project")} type="button">
                    Save existing-project match
                  </button>
                  <button className="secondary-button" disabled={isPending} onClick={() => handleMatch("new_project_needed")} type="button">
                    Mark new project needed
                  </button>
                  <button className="secondary-button" disabled={isPending} onClick={() => handleMatch("ambiguous_match")} type="button">
                    Mark ambiguous
                  </button>
                  <button className="secondary-button" disabled={isPending} onClick={() => handleMatch("ignored")} type="button">
                    Ignore candidate
                  </button>
                </div>
              </div>

              <div className="admin-form-card section-stack">
                <div>
                  <p className="eyebrow">Compare</p>
                  <h3>Canonical vs incoming values</h3>
                </div>

                {candidate.compareRows.length > 0 ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Field</th>
                          <th>Canonical</th>
                          <th>Incoming</th>
                          <th>Raw source</th>
                          <th>Source</th>
                          <th>Trust</th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidate.compareRows.map((row) => (
                          <tr key={row.fieldName}>
                            <td>{row.fieldName}</td>
                            <td>{row.canonicalValue ?? "Null"}</td>
                            <td>{row.stagingValue ?? "Null"}</td>
                            <td>{row.rawSourceValue ?? "Null"}</td>
                            <td>{[row.sourcePage ? `p.${row.sourcePage}` : null, row.sourceSection].filter(Boolean).join(" | ") || "Manual review"}</td>
                            <td>
                              <div className="stacked-cell">
                                <span>{row.valueOriginType}</span>
                                <span className="muted-copy">{row.confidenceLevel}</span>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-state">
                    <strong>No compare rows yet.</strong>
                    <p className="panel-copy">Compare rows appear once the candidate can be evaluated against canonical values.</p>
                  </div>
                )}

                {candidate.diffSummary.length > 0 ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Field</th>
                          <th>Previous snapshot</th>
                          <th>Incoming snapshot</th>
                          <th>Changed</th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidate.diffSummary.map((row) => (
                          <tr key={row.fieldName}>
                            <td>{row.fieldName}</td>
                            <td>{row.previousValue ?? "Null"}</td>
                            <td>{row.incomingValue ?? "Null"}</td>
                            <td>{row.changed ? "yes" : "no"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>

              <div className="admin-form-card section-stack">
                <div>
                  <p className="eyebrow">Publish</p>
                  <h3>Canonical publish preview</h3>
                </div>

                <div className="stats-grid">
                  <div>
                    <strong>{formatNumber(candidate.totalUnits)}</strong>
                    <span>Total units</span>
                  </div>
                  <div>
                    <strong>{formatNumber(candidate.marketedUnits)}</strong>
                    <span>Marketed units</span>
                  </div>
                  <div>
                    <strong>{formatNumber(candidate.soldUnitsCumulative)}</strong>
                    <span>Sold cumulative</span>
                  </div>
                  <div>
                    <strong>{formatNumber(candidate.unsoldUnits)}</strong>
                    <span>Unsold units</span>
                  </div>
                  <div>
                    <strong>{formatCurrency(candidate.avgPricePerSqmCumulative)}</strong>
                    <span>Avg price per sqm</span>
                  </div>
                  <div>
                    <strong>{formatPercent(candidate.grossMarginExpectedPct)}</strong>
                    <span>Gross margin</span>
                  </div>
                </div>

                <div className="form-actions">
                  <button
                    className="primary-button"
                    disabled={
                      isPending ||
                      candidate.matchingStatus === "unmatched" ||
                      candidate.matchingStatus === "ambiguous_match"
                    }
                    onClick={handlePublishCandidate}
                    type="button"
                  >
                    Publish to canonical
                  </button>
                  {candidate.matchedProjectId ? (
                    <Link className="inline-link" href={`/admin/projects/${candidate.matchedProjectId}`}>
                      Open canonical project
                    </Link>
                  ) : null}
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
