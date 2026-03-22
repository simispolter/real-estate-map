"use client";

import type { AdminCoverageDashboard, AdminCoverageCompany } from "@real-estat-map/shared";
import { useMemo, useState, useTransition } from "react";

import { updateAdminCoverage } from "@/lib/api";

const COVERAGE_PRIORITIES = ["high", "medium", "low"] as const;
const HISTORICAL_COVERAGE_STATUSES = ["not_started", "partial", "current_only", "historical_complete"] as const;

type CoverageDraft = {
  isInScope: boolean;
  outOfScopeReason: string;
  coveragePriority: string;
  historicalCoverageStatus: string;
  notes: string;
};

function buildDrafts(companies: AdminCoverageCompany[]) {
  return Object.fromEntries(
    companies.map((company) => [
      company.companyId,
      {
        isInScope: company.isInScope,
        outOfScopeReason: company.outOfScopeReason ?? "",
        coveragePriority: company.coveragePriority,
        historicalCoverageStatus: company.historicalCoverageStatus,
        notes: company.notes ?? "",
      } satisfies CoverageDraft,
    ]),
  );
}

export function AdminCoverageDashboardPanel({ initialItem }: { initialItem: AdminCoverageDashboard }) {
  const [dashboard, setDashboard] = useState(initialItem);
  const [drafts, setDrafts] = useState<Record<string, CoverageDraft>>(() => buildDrafts(initialItem.companies));
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const summaryCards = useMemo(
    () => [
      { label: "Companies in scope", value: dashboard.summary.companiesInScope },
      { label: "Reports registered", value: dashboard.summary.reportsRegistered },
      { label: "Projects created", value: dashboard.summary.projectsCreated },
      { label: "Snapshots created", value: dashboard.summary.snapshotsCreated },
      { label: "Unmatched candidates", value: dashboard.summary.unmatchedCandidates },
      { label: "Ambiguous candidates", value: dashboard.summary.ambiguousCandidates },
      { label: "Missing key fields", value: dashboard.summary.projectsMissingKeyFields },
      { label: "Missing precise location", value: dashboard.summary.projectsMissingPreciseLocation },
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
        is_in_scope: draft.isInScope,
        out_of_scope_reason: draft.outOfScopeReason || null,
        coverage_priority: draft.coveragePriority,
        historical_coverage_status: draft.historicalCoverageStatus,
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
                      <strong>{company.companyNameHe}</strong>
                      <p className="panel-copy">
                        Latest ingested report: {company.latestReportName ?? "None yet"}
                      </p>
                    </div>
                    <div className="tag-row">
                      <span className="tag">{company.reportsRegistered} reports</span>
                      <span className="tag">{company.projectsCreated} projects</span>
                      <span className="tag">{company.snapshotsCreated} snapshots</span>
                    </div>
                  </div>

                  <div className="admin-form-grid">
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
