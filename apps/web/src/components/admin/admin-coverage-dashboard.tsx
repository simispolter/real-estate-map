"use client";

import type { AdminCoverageDashboard, AdminCoverageCompany } from "@real-estat-map/shared";
import { useMemo, useState, useTransition } from "react";

import { applyAdminCoverageBulk, updateAdminCoverage } from "@/lib/api";

const COVERAGE_PRIORITIES = ["high", "medium", "low"] as const;
const HISTORICAL_COVERAGE_STATUSES = ["not_started", "partial", "current_only", "historical_complete"] as const;
const BACKFILL_STATUSES = ["not_started", "current_cycle_only", "historical_backfill", "complete", "blocked"] as const;

type CoverageDraft = {
  isActive: boolean;
  isInScope: boolean;
  outOfScopeReason: string;
  coveragePriority: string;
  historicalCoverageStatus: string;
  backfillStatus: string;
  notes: string;
};

function buildDrafts(companies: AdminCoverageCompany[]) {
  return Object.fromEntries(
    companies.map((company) => [
      company.companyId,
      {
        isActive: company.isActive,
        isInScope: company.isInScope,
        outOfScopeReason: company.outOfScopeReason ?? "",
        coveragePriority: company.coveragePriority,
        historicalCoverageStatus: company.historicalCoverageStatus,
        backfillStatus: company.backfillStatus,
        notes: company.notes ?? "",
      } satisfies CoverageDraft,
    ]),
  );
}

export function AdminCoverageDashboardPanel({ initialItem }: { initialItem: AdminCoverageDashboard }) {
  const [dashboard, setDashboard] = useState(initialItem);
  const [drafts, setDrafts] = useState<Record<string, CoverageDraft>>(() => buildDrafts(initialItem.companies));
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<string[]>([]);
  const [bulkAction, setBulkAction] = useState<"set_scope" | "set_backfill_status">("set_scope");
  const [bulkScope, setBulkScope] = useState<"in_scope" | "out_of_scope">("in_scope");
  const [bulkBackfillStatus, setBulkBackfillStatus] = useState<string>("historical_backfill");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const summaryCards = useMemo(
    () => [
      { label: "Companies in scope", value: dashboard.summary.companiesInScope },
      { label: "Latest report ingested", value: dashboard.summary.companiesWithLatestReportIngested },
      { label: "Missing latest report", value: dashboard.summary.companiesMissingLatestReport },
      { label: "Reports registered", value: dashboard.summary.reportsRegistered },
      { label: "Reports published", value: dashboard.summary.reportsPublishedIntoCanonical },
      { label: "Projects created", value: dashboard.summary.projectsCreated },
      { label: "Snapshots created", value: dashboard.summary.snapshotsCreated },
      { label: "Unmatched candidates", value: dashboard.summary.unmatchedCandidates },
      { label: "Ambiguous candidates", value: dashboard.summary.ambiguousCandidates },
      { label: "Missing key fields", value: dashboard.summary.projectsMissingKeyFields },
      { label: "City-only / unknown", value: dashboard.summary.projectsCityOnlyLocation },
      { label: "Exact / approximate", value: dashboard.summary.projectsWithExactOrApproximateGeometry },
    ],
    [dashboard.summary],
  );

  function saveCompany(companyId: string) {
    const draft = drafts[companyId];
    if (!draft) {
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const result = await updateAdminCoverage(companyId, {
        is_active: draft.isActive,
        is_in_scope: draft.isInScope,
        out_of_scope_reason: draft.outOfScopeReason || null,
        coverage_priority: draft.coveragePriority,
        historical_coverage_status: draft.historicalCoverageStatus,
        backfill_status: draft.backfillStatus,
        notes: draft.notes || null,
      });
      if (!result.item) {
        setFeedback("Could not save coverage settings.");
        return;
      }
      setDashboard(result.item);
      setDrafts(buildDrafts(result.item.companies));
      setFeedback("Coverage registry updated.");
    });
  }

  function runBulkAction() {
    if (selectedCompanyIds.length === 0) {
      setFeedback("Select at least one company for a bulk action.");
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const result = await applyAdminCoverageBulk({
        target_type: "company",
        action: bulkAction,
        ids: selectedCompanyIds,
        is_in_scope: bulkAction === "set_scope" ? bulkScope === "in_scope" : undefined,
        backfill_status: bulkAction === "set_backfill_status" ? bulkBackfillStatus : undefined,
      });
      if (!result.item) {
        setFeedback("Bulk coverage update failed.");
        return;
      }
      const refreshed = await updateAdminCoverage(selectedCompanyIds[0], {});
      if (!refreshed.item) {
        setFeedback("Bulk coverage update ran, but the dashboard could not refresh.");
        return;
      }
      setDashboard(refreshed.item);
      setDrafts(buildDrafts(refreshed.item.companies));
      setSelectedCompanyIds([]);
      setFeedback(`Bulk coverage update applied to ${result.item.appliedCount} companies.`);
    });
  }

  return (
    <div className="section-stack">
      {feedback ? <p className="muted-copy">{feedback}</p> : null}

      <div className="stats-grid">
        {summaryCards.map((card) => (
          <div key={card.label}>
            <strong>{card.value}</strong>
            <span>{card.label}</span>
          </div>
        ))}
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Company Coverage</p>
          <h3>Backfill and operations registry</h3>
          <p className="panel-copy">
            Track in-scope coverage, current ingestion posture, and which companies still need report and snapshot backfill.
          </p>
        </div>

        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Bulk action</span>
            <select value={bulkAction} onChange={(event) => setBulkAction(event.target.value as "set_scope" | "set_backfill_status")}>
              <option value="set_scope">Set in-scope flag</option>
              <option value="set_backfill_status">Set backfill status</option>
            </select>
          </label>
          {bulkAction === "set_scope" ? (
            <label className="filter-field">
              <span>Scope value</span>
              <select value={bulkScope} onChange={(event) => setBulkScope(event.target.value as "in_scope" | "out_of_scope")}>
                <option value="in_scope">In scope</option>
                <option value="out_of_scope">Out of scope</option>
              </select>
            </label>
          ) : (
            <label className="filter-field">
              <span>Backfill status</span>
              <select value={bulkBackfillStatus} onChange={(event) => setBulkBackfillStatus(event.target.value)}>
                {BACKFILL_STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="form-actions">
            <button className="primary-button" disabled={isPending || selectedCompanyIds.length === 0} onClick={runBulkAction} type="button">
              Apply to {selectedCompanyIds.length} selected
            </button>
          </div>
        </div>

        {dashboard.fieldCompleteness.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Complete</th>
                  <th>Missing</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.fieldCompleteness.map((item) => (
                  <tr key={item.fieldName}>
                    <td>{item.fieldName}</td>
                    <td>{item.completeCount}</td>
                    <td>{item.missingCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {dashboard.companies.length > 0 ? (
          <div className="section-stack">
            {dashboard.companies.map((company) => {
              const draft = drafts[company.companyId];
              if (!draft) {
                return null;
              }

              return (
                <div className="admin-form-card section-stack" key={company.companyId}>
                  <div className="candidate-queue-header">
                    <div>
                      <label className="panel-copy">
                        <input
                          checked={selectedCompanyIds.includes(company.companyId)}
                          type="checkbox"
                          onChange={(event) =>
                            setSelectedCompanyIds((current) =>
                              event.target.checked
                                ? [...current, company.companyId]
                                : current.filter((value) => value !== company.companyId),
                            )
                          }
                        />{" "}
                        Select
                      </label>
                      <strong>{company.companyNameHe}</strong>
                      <p className="panel-copy">
                        Latest registered: {company.latestReportRegisteredName ?? "None yet"} | Latest ingested:{" "}
                        {company.latestReportIngestedName ?? "None yet"}
                      </p>
                    </div>
                    <div className="tag-row">
                      <span className="tag">{company.backfillStatus}</span>
                      <span className="tag">{company.reportsRegistered} reports</span>
                      <span className="tag">{company.projectsCreated} projects</span>
                      <span className="tag">{company.snapshotsCreated} snapshots</span>
                    </div>
                  </div>

                  <div className="admin-form-grid">
                    <label className="panel-copy">
                      <input
                        checked={draft.isActive}
                        type="checkbox"
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [company.companyId]: { ...draft, isActive: event.target.checked },
                          }))
                        }
                      />{" "}
                      Company is active
                    </label>
                    <label className="panel-copy">
                      <input
                        checked={draft.isInScope}
                        type="checkbox"
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [company.companyId]: { ...draft, isInScope: event.target.checked },
                          }))
                        }
                      />{" "}
                      Company is in scope
                    </label>
                    <label className="filter-field">
                      <span>Coverage priority</span>
                      <select
                        value={draft.coveragePriority}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [company.companyId]: { ...draft, coveragePriority: event.target.value },
                          }))
                        }
                      >
                        {COVERAGE_PRIORITIES.map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="filter-field">
                      <span>Historical coverage</span>
                      <select
                        value={draft.historicalCoverageStatus}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [company.companyId]: { ...draft, historicalCoverageStatus: event.target.value },
                          }))
                        }
                      >
                        {HISTORICAL_COVERAGE_STATUSES.map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="filter-field">
                      <span>Backfill status</span>
                      <select
                        value={draft.backfillStatus}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [company.companyId]: { ...draft, backfillStatus: event.target.value },
                          }))
                        }
                      >
                        {BACKFILL_STATUSES.map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="filter-field">
                      <span>Out-of-scope reason</span>
                      <input
                        value={draft.outOfScopeReason}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [company.companyId]: { ...draft, outOfScopeReason: event.target.value },
                          }))
                        }
                      />
                    </label>
                    <label className="filter-field">
                      <span>Ops notes</span>
                      <textarea
                        value={draft.notes}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [company.companyId]: { ...draft, notes: event.target.value },
                          }))
                        }
                      />
                    </label>
                  </div>

                  <div className="tag-row">
                    <span className="tag">{company.projectsMissingKeyFields} missing key fields</span>
                    <span className="tag">{company.projectsCityOnlyLocation} city-only / unknown</span>
                    <span className="tag">{company.projectsWithExactOrApproximateGeometry} exact / approximate</span>
                    {company.latestReportPublished ? <span className="tag">published {company.latestReportPublished}</span> : null}
                  </div>

                  <div className="form-actions">
                    <button className="primary-button" disabled={isPending} onClick={() => saveCompany(company.companyId)} type="button">
                      Save coverage
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-state">
            <strong>No coverage rows are available yet.</strong>
            <p className="panel-copy">Once companies exist in the canonical registry, coverage controls will appear here automatically.</p>
          </div>
        )}
      </div>
    </div>
  );
}
