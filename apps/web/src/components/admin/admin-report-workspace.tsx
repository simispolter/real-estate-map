"use client";

import type { AdminCandidateDetail, AdminParserRun, AdminReportDetail, AdminReportQa } from "@real-estat-map/shared";
import {
  PERMIT_STATUSES,
  PROJECT_BUSINESS_TYPES,
  PROJECT_DISCLOSURE_LEVELS,
  PROJECT_LIFECYCLE_STAGES,
  PROJECT_STATUSES,
  REPORT_INGESTION_STATUSES,
  SOURCE_SECTION_KINDS,
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
  formatDate,
  formatDisclosureLevelLabel,
  formatEnumLabel,
  formatLifecycleStageLabel,
  formatSectionKindLabel,
} from "@/lib/format";

type ReportFormState = {
  ingestion_status: string;
  published_at: string;
  source_url: string;
  source_file_path: string;
  source_label: string;
  notes: string;
};

type CandidateFormState = {
  candidate_project_name: string;
  city: string;
  neighborhood: string;
  candidate_lifecycle_stage: string;
  candidate_disclosure_level: string;
  candidate_section_kind: string;
  project_business_type: string;
  project_status: string;
  permit_status: string;
  location_confidence: string;
  review_notes: string;
};

function reportFormFromItem(report: AdminReportDetail): ReportFormState {
  return {
    ingestion_status: report.ingestionStatus,
    published_at: report.publishedAt ?? "",
    source_url: report.sourceUrl ?? "",
    source_file_path: report.sourceFilePath ?? "",
    source_label: report.sourceLabel ?? "",
    notes: report.notes ?? "",
  };
}

function candidateFormFromItem(candidate: AdminCandidateDetail): CandidateFormState {
  return {
    candidate_project_name: candidate.candidateProjectName,
    city: candidate.city ?? "",
    neighborhood: candidate.neighborhood ?? "",
    candidate_lifecycle_stage: candidate.candidateLifecycleStage ?? "",
    candidate_disclosure_level: candidate.candidateDisclosureLevel ?? "",
    candidate_section_kind: candidate.candidateSectionKind ?? "",
    project_business_type: candidate.projectBusinessType ?? "regular_dev",
    project_status: candidate.projectStatus ?? "",
    permit_status: candidate.permitStatus ?? "",
    location_confidence: candidate.locationConfidence,
    review_notes: candidate.reviewNotes ?? "",
  };
}

function emptyManualCandidateState(): CandidateFormState {
  return {
    candidate_project_name: "",
    city: "",
    neighborhood: "",
    candidate_lifecycle_stage: "",
    candidate_disclosure_level: "",
    candidate_section_kind: "",
    project_business_type: "regular_dev",
    project_status: "",
    permit_status: "",
    location_confidence: "city_only",
    review_notes: "",
  };
}

function setQueryParam(
  pathname: string,
  currentSearchParams: URLSearchParams,
  key: string,
  value: string | null,
  router: ReturnType<typeof useRouter>,
) {
  const next = new URLSearchParams(currentSearchParams.toString());
  if (value && value.trim() !== "") {
    next.set(key, value);
  } else {
    next.delete(key);
  }
  router.replace(next.size > 0 ? `${pathname}?${next.toString()}` : pathname, { scroll: false });
}

function optionLabel(value: string) {
  return formatEnumLabel(value);
}

export function AdminReportWorkspace({
  initialCandidateId,
  initialReport,
}: {
  initialCandidateId: string | null;
  initialReport: AdminReportDetail;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [report, setReport] = useState(initialReport);
  const [reportForm, setReportForm] = useState<ReportFormState>(() => reportFormFromItem(initialReport));
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(
    initialCandidateId ?? initialReport.candidates[0]?.id ?? null,
  );
  const [candidate, setCandidate] = useState<AdminCandidateDetail | null>(null);
  const [candidateForm, setCandidateForm] = useState<CandidateFormState | null>(null);
  const [manualCandidate, setManualCandidate] = useState<CandidateFormState>(emptyManualCandidateState());
  const [qa, setQa] = useState<AdminReportQa | null>(null);
  const [parserRuns, setParserRuns] = useState<AdminParserRun[]>([]);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    setReport(initialReport);
    setReportForm(reportFormFromItem(initialReport));
  }, [initialReport]);

  useEffect(() => {
    startTransition(async () => {
      const [qaResult, parserRunsResult] = await Promise.all([
        getAdminReportQa(initialReport.id),
        getAdminReportParserRuns(initialReport.id),
      ]);
      setQa(qaResult.item);
      setParserRuns(parserRunsResult.items);
    });
  }, [initialReport.id]);

  useEffect(() => {
    if (!selectedCandidateId) {
      setCandidate(null);
      setCandidateForm(null);
      return;
    }

    startTransition(async () => {
      const result = await getAdminCandidateDetail(selectedCandidateId);
      if (!result.item) {
        setCandidate(null);
        setCandidateForm(null);
        return;
      }
      setCandidate(result.item);
      setCandidateForm(candidateFormFromItem(result.item));
    });
  }, [selectedCandidateId]);

  const latestParserRun = parserRuns[0] ?? qa?.latestParserRun ?? null;
  const suppressedRowsByReason = useMemo(() => {
    const diagnostics = latestParserRun?.diagnostics;
    const raw = diagnostics?.suppressed_rows_by_reason;
    return raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  }, [latestParserRun]);
  const canPublish =
    candidate?.matchingStatus === "matched_existing_project" || candidate?.matchingStatus === "new_project_needed";

  function selectCandidate(candidateId: string | null) {
    setSelectedCandidateId(candidateId);
    setQueryParam(pathname, new URLSearchParams(searchParams.toString()), "candidate", candidateId, router);
  }

  async function refreshReportAndCandidate(nextCandidateId?: string | null) {
    const reportResult = await getAdminReportDetail(report.id);
    if (reportResult.item) {
      setReport(reportResult.item);
      setReportForm(reportFormFromItem(reportResult.item));
      if (!selectedCandidateId && reportResult.item.candidates[0]) {
        setSelectedCandidateId(reportResult.item.candidates[0].id);
      }
    }

    const [qaResult, parserRunsResult] = await Promise.all([
      getAdminReportQa(report.id),
      getAdminReportParserRuns(report.id),
    ]);
    setQa(qaResult.item);
    setParserRuns(parserRunsResult.items);

    const candidateId = nextCandidateId ?? selectedCandidateId;
    if (candidateId) {
      const candidateResult = await getAdminCandidateDetail(candidateId);
      setCandidate(candidateResult.item);
      setCandidateForm(candidateResult.item ? candidateFormFromItem(candidateResult.item) : null);
    }
  }

  function handleSaveReport() {
    startTransition(async () => {
      setFeedback(null);
      const result = await updateAdminReport(report.id, {
        ingestion_status: reportForm.ingestion_status,
        published_at: reportForm.published_at || null,
        source_url: reportForm.source_url || null,
        source_file_path: reportForm.source_file_path || null,
        source_label: reportForm.source_label || null,
        notes: reportForm.notes || null,
      });
      if (!result.item) {
        setFeedback("Could not update the source record.");
        return;
      }
      setReport(result.item);
      setReportForm(reportFormFromItem(result.item));
      setFeedback("Source record updated.");
    });
  }

  function handleRunExtraction() {
    startTransition(async () => {
      setFeedback(null);
      const result = await runAdminReportExtraction(report.id);
      if (!result.item) {
        setFeedback("Extraction could not be started.");
        return;
      }
      setReport(result.item);
      await refreshReportAndCandidate(result.item.candidates[0]?.id ?? selectedCandidateId);
      setFeedback("Extraction finished and staging candidates were refreshed.");
    });
  }

  function handleCreateManualCandidate() {
    startTransition(async () => {
      setFeedback(null);
      const result = await createAdminCandidate(report.id, {
        candidate_project_name: manualCandidate.candidate_project_name,
        city: manualCandidate.city || null,
        neighborhood: manualCandidate.neighborhood || null,
        candidate_lifecycle_stage: manualCandidate.candidate_lifecycle_stage || null,
        candidate_disclosure_level: manualCandidate.candidate_disclosure_level || null,
        candidate_section_kind: manualCandidate.candidate_section_kind || null,
        project_business_type: manualCandidate.project_business_type,
        project_status: manualCandidate.project_status || null,
        permit_status: manualCandidate.permit_status || null,
        location_confidence: manualCandidate.location_confidence,
        value_origin_type: "manual",
        confidence_level: "medium",
        review_status: "pending",
        review_notes: manualCandidate.review_notes || null,
      });
      if (!result.item) {
        setFeedback("Could not create a manual candidate.");
        return;
      }
      setManualCandidate(emptyManualCandidateState());
      await refreshReportAndCandidate(result.item.id);
      selectCandidate(result.item.id);
      setFeedback("Manual candidate created.");
    });
  }

  function handleSaveCandidate() {
    if (!candidate || !candidateForm) {
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const result = await updateAdminCandidate(candidate.id, {
        candidate_project_name: candidateForm.candidate_project_name,
        city: candidateForm.city || null,
        neighborhood: candidateForm.neighborhood || null,
        candidate_lifecycle_stage: candidateForm.candidate_lifecycle_stage || null,
        candidate_disclosure_level: candidateForm.candidate_disclosure_level || null,
        candidate_section_kind: candidateForm.candidate_section_kind || null,
        project_business_type: candidateForm.project_business_type,
        project_status: candidateForm.project_status || null,
        permit_status: candidateForm.permit_status || null,
        location_confidence: candidateForm.location_confidence,
        review_notes: candidateForm.review_notes || null,
        review_status: "pending",
      });
      if (!result.item) {
        setFeedback("Could not save the candidate review.");
        return;
      }
      setCandidate(result.item);
      setCandidateForm(candidateFormFromItem(result.item));
      await refreshReportAndCandidate(result.item.id);
      setFeedback("Candidate review updated.");
    });
  }

  function handleMatch(matchStatus: string, matchedProjectId?: string | null) {
    if (!candidate) {
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const result = await matchAdminCandidate(candidate.id, {
        match_status: matchStatus,
        matched_project_id: matchedProjectId || null,
        reviewer_note: candidateForm?.review_notes || null,
      });
      if (!result.item) {
        setFeedback("Could not update the match decision.");
        return;
      }
      setCandidate(result.item);
      setCandidateForm(candidateFormFromItem(result.item));
      await refreshReportAndCandidate(result.item.id);
      setFeedback("Match decision saved.");
    });
  }

  function handlePublish() {
    if (!candidate) {
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const result = await publishAdminCandidate(candidate.id, {
        reviewer_note: candidateForm?.review_notes || null,
      });
      if (!result.item) {
        setFeedback("Publish failed. Make sure the candidate is reviewed and matched or marked as a new project.");
        return;
      }
      setCandidate(result.item);
      setCandidateForm(candidateFormFromItem(result.item));
      await refreshReportAndCandidate(result.item.id);
      setFeedback("Candidate published into the canonical database.");
    });
  }

  return (
    <div className="section-stack">
      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Working Core</p>
          <h2>Report to canonical database</h2>
          <p className="panel-copy">
            Keep this workflow simple: register the report, run extraction, review candidates, then publish canonical projects and snapshots.
          </p>
        </div>

        {feedback ? <p className="muted-copy">{feedback}</p> : null}

        <div className="tag-row">
          <span className="tag">{report.companyNameHe}</span>
          <span className="tag">{formatDate(report.periodEndDate)}</span>
          <span className="tag">{report.ingestionStatus}</span>
          <span className="tag">{report.candidateCount} candidates</span>
        </div>

        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Ingestion status</span>
            <select
              value={reportForm.ingestion_status}
              onChange={(event) => setReportForm((current) => ({ ...current, ingestion_status: event.target.value }))}
            >
              {REPORT_INGESTION_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Published at</span>
            <input
              type="date"
              value={reportForm.published_at}
              onChange={(event) => setReportForm((current) => ({ ...current, published_at: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Source label</span>
            <input
              value={reportForm.source_label}
              onChange={(event) => setReportForm((current) => ({ ...current, source_label: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Source URL</span>
            <input
              value={reportForm.source_url}
              onChange={(event) => setReportForm((current) => ({ ...current, source_url: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Source file path</span>
            <input
              value={reportForm.source_file_path}
              onChange={(event) => setReportForm((current) => ({ ...current, source_file_path: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Notes</span>
            <textarea value={reportForm.notes} onChange={(event) => setReportForm((current) => ({ ...current, notes: event.target.value }))} />
          </label>
        </div>

        <div className="form-actions">
          <button className="primary-button" disabled={isPending} onClick={handleSaveReport} type="button">
            Save source metadata
          </button>
          <button className="secondary-button" disabled={isPending} onClick={handleRunExtraction} type="button">
            Run extraction
          </button>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Extraction Summary</p>
          <h3>What the parser found</h3>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <tbody>
              <tr>
                <th>Total candidates</th>
                <td>{qa?.summary.totalCandidates ?? report.candidateCount}</td>
                <th>Matched existing</th>
                <td>{qa?.summary.matchedExistingProjects ?? 0}</td>
              </tr>
              <tr>
                <th>New projects needed</th>
                <td>{qa?.summary.newProjectsNeeded ?? 0}</td>
                <th>Ambiguous</th>
                <td>{qa?.summary.ambiguousCandidates ?? 0}</td>
              </tr>
              <tr>
                <th>Published</th>
                <td>{qa?.summary.publishedCandidates ?? 0}</td>
                <th>Missing key fields</th>
                <td>{qa?.summary.missingKeyFieldTotal ?? 0}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {latestParserRun ? (
          <details>
            <summary>Latest parser diagnostics</summary>
            <div className="section-stack">
              <div className="tag-row">
                <span className="tag">status: {latestParserRun.status}</span>
                <span className="tag">sections: {latestParserRun.sectionsFound}</span>
                <span className="tag">candidates: {latestParserRun.candidateCount}</span>
                <span className="tag">fields: {latestParserRun.fieldCandidateCount}</span>
              </div>
              {Object.keys(suppressedRowsByReason).length > 0 ? (
                <div className="tag-row">
                  {Object.entries(suppressedRowsByReason).map(([reason, count]) => (
                    <span key={reason} className="tag">
                      {reason}: {String(count)}
                    </span>
                  ))}
                </div>
              ) : null}
              {latestParserRun.warnings.length > 0 ? (
                <div className="empty-state">
                  <strong>Warnings</strong>
                  <p className="panel-copy">{latestParserRun.warnings.join(" | ")}</p>
                </div>
              ) : null}
            </div>
          </details>
        ) : null}
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Manual Catch-up</p>
          <h3>Add a missing candidate</h3>
          <p className="panel-copy">Use this only when extraction missed a project row. It still goes into staging first.</p>
        </div>
        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Candidate project name</span>
            <input
              value={manualCandidate.candidate_project_name}
              onChange={(event) => setManualCandidate((current) => ({ ...current, candidate_project_name: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>City</span>
            <input value={manualCandidate.city} onChange={(event) => setManualCandidate((current) => ({ ...current, city: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Lifecycle stage</span>
            <select
              value={manualCandidate.candidate_lifecycle_stage}
              onChange={(event) => setManualCandidate((current) => ({ ...current, candidate_lifecycle_stage: event.target.value }))}
            >
              <option value="">Unknown</option>
              {PROJECT_LIFECYCLE_STAGES.map((value) => (
                <option key={value} value={value}>
                  {formatLifecycleStageLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Disclosure depth</span>
            <select
              value={manualCandidate.candidate_disclosure_level}
              onChange={(event) => setManualCandidate((current) => ({ ...current, candidate_disclosure_level: event.target.value }))}
            >
              <option value="">Unknown</option>
              {PROJECT_DISCLOSURE_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {formatDisclosureLevelLabel(value)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button
            className="secondary-button"
            disabled={isPending || !manualCandidate.candidate_project_name.trim()}
            onClick={handleCreateManualCandidate}
            type="button"
          >
            Add manual candidate
          </button>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Candidates</p>
          <h3>Review queue for this report</h3>
          <p className="panel-copy">Pick a candidate, correct the core fields, decide whether it matches an existing project or needs a new one, then publish.</p>
        </div>

        {report.candidates.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>City</th>
                  <th>Lifecycle</th>
                  <th>Disclosure</th>
                  <th>Match</th>
                  <th>Publish</th>
                </tr>
              </thead>
              <tbody>
                {report.candidates.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <button className="inline-link" onClick={() => selectCandidate(item.id)} type="button">
                        {item.candidateProjectName}
                      </button>
                    </td>
                    <td>{item.city ?? "Unknown"}</td>
                    <td>{formatLifecycleStageLabel(item.candidateLifecycleStage)}</td>
                    <td>{formatDisclosureLevelLabel(item.candidateDisclosureLevel)}</td>
                    <td>{item.matchedProjectName ?? formatEnumLabel(item.matchingStatus)}</td>
                    <td>{formatEnumLabel(item.publishStatus)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No staging candidates are available yet.</strong>
            <p className="panel-copy">Run extraction or add a manual candidate to start the review flow.</p>
          </div>
        )}
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Candidate Review</p>
          <h3>{candidate?.candidateProjectName ?? "Choose a candidate"}</h3>
        </div>

        {candidate && candidateForm ? (
          <>
            <div className="tag-row">
              <span className="tag">confidence: {candidate.confidenceLevel}</span>
              <span className="tag">match: {formatEnumLabel(candidate.matchingStatus)}</span>
              <span className="tag">publish: {formatEnumLabel(candidate.publishStatus)}</span>
              <span className="tag">section: {formatSectionKindLabel(candidate.candidateSectionKind)}</span>
            </div>

            <div className="admin-form-grid">
              <label className="filter-field">
                <span>Project name</span>
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
                  <option value="">Unknown</option>
                  {PROJECT_LIFECYCLE_STAGES.map((value) => (
                    <option key={value} value={value}>
                      {formatLifecycleStageLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Disclosure depth</span>
                <select
                  value={candidateForm.candidate_disclosure_level}
                  onChange={(event) =>
                    setCandidateForm((current) => (current ? { ...current, candidate_disclosure_level: event.target.value } : current))
                  }
                >
                  <option value="">Unknown</option>
                  {PROJECT_DISCLOSURE_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {formatDisclosureLevelLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Section family</span>
                <select
                  value={candidateForm.candidate_section_kind}
                  onChange={(event) =>
                    setCandidateForm((current) => (current ? { ...current, candidate_section_kind: event.target.value } : current))
                  }
                >
                  <option value="">Unknown</option>
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
                      {optionLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Project status</span>
                <select
                  value={candidateForm.project_status}
                  onChange={(event) => setCandidateForm((current) => (current ? { ...current, project_status: event.target.value } : current))}
                >
                  <option value="">Unknown</option>
                  {PROJECT_STATUSES.map((value) => (
                    <option key={value} value={value}>
                      {optionLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Permit status</span>
                <select
                  value={candidateForm.permit_status}
                  onChange={(event) => setCandidateForm((current) => (current ? { ...current, permit_status: event.target.value } : current))}
                >
                  <option value="">Unknown</option>
                  {PERMIT_STATUSES.map((value) => (
                    <option key={value} value={value}>
                      {optionLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field">
                <span>Reviewer note</span>
                <textarea
                  value={candidateForm.review_notes}
                  onChange={(event) => setCandidateForm((current) => (current ? { ...current, review_notes: event.target.value } : current))}
                />
              </label>
            </div>

            <div className="form-actions">
              <button className="primary-button" disabled={isPending} onClick={handleSaveCandidate} type="button">
                Save review
              </button>
              <button className="secondary-button" disabled={isPending} onClick={() => handleMatch("new_project_needed")} type="button">
                Create as new project
              </button>
              <button className="secondary-button" disabled={isPending} onClick={() => handleMatch("ignored")} type="button">
                Ignore row
              </button>
              <button className="secondary-button" disabled={isPending || !canPublish} onClick={handlePublish} type="button">
                Publish snapshot
              </button>
              {candidate.matchedProjectId ? (
                <Link className="secondary-button" href={`/admin/projects/${candidate.matchedProjectId}`}>
                  Open canonical project
                </Link>
              ) : null}
            </div>

            {candidate.matchSuggestions.length > 0 ? (
              <div className="section-stack">
                <div>
                  <p className="eyebrow">Match Suggestions</p>
                  <h4>Existing canonical projects</h4>
                </div>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Project</th>
                        <th>City</th>
                        <th>Score</th>
                        <th>State</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {candidate.matchSuggestions.map((suggestion) => (
                        <tr key={suggestion.projectId}>
                          <td>{suggestion.canonicalName}</td>
                          <td>{suggestion.city ?? "Unknown"}</td>
                          <td>{suggestion.similarityScore.toFixed(2)}</td>
                          <td>{formatEnumLabel(suggestion.matchState)}</td>
                          <td>
                            <button className="inline-link" onClick={() => handleMatch("matched_existing_project", suggestion.projectId)} type="button">
                              Match this project
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}

            <details>
              <summary>Compare and source evidence</summary>
              <div className="section-stack">
                {candidate.compareRows.length > 0 ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Field</th>
                          <th>Canonical</th>
                          <th>Incoming</th>
                          <th>Raw source</th>
                          <th>Page</th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidate.compareRows.map((row) => (
                          <tr key={row.fieldName}>
                            <td>{row.fieldName}</td>
                            <td>{row.canonicalValue ?? "-"}</td>
                            <td>{row.stagingValue ?? "-"}</td>
                            <td>{row.rawSourceValue ?? "-"}</td>
                            <td>{row.sourcePage ?? "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}

                {candidate.fieldCandidates.length > 0 ? (
                  <div className="empty-state">
                    <strong>Field rows</strong>
                    <p className="panel-copy">
                      {candidate.fieldCandidates
                        .slice(0, 6)
                        .map((item) => `${item.fieldName}: ${item.normalizedValue ?? item.rawValue ?? "-"} (p.${item.sourcePage ?? "?"})`)
                        .join(" | ")}
                    </p>
                  </div>
                ) : null}

                {candidate.addressCandidates.length > 0 ? (
                  <div className="empty-state">
                    <strong>Address rows</strong>
                    <p className="panel-copy">
                      {candidate.addressCandidates
                        .map((item) =>
                          formatAddressLabel({
                            addressTextRaw: item.addressTextRaw,
                            street: item.street,
                            houseNumberFrom: item.houseNumberFrom,
                            houseNumberTo: item.houseNumberTo,
                            city: item.city,
                          }),
                        )
                        .join(" | ")}
                    </p>
                  </div>
                ) : null}
              </div>
            </details>
          </>
        ) : (
          <div className="empty-state">
            <strong>No candidate selected yet.</strong>
            <p className="panel-copy">Pick a candidate from the table above to review, match, and publish it into the canonical database.</p>
          </div>
        )}
      </div>
    </div>
  );
}
