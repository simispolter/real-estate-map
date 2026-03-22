"use client";

import type { AdminReportSummary, CompanyListItem } from "@real-estat-map/shared";
import { useState, useTransition } from "react";

import { createAdminReport } from "@/lib/api";
import { formatDate } from "@/lib/format";

const REPORT_TYPES = ["annual", "q1", "q2", "q3", "prospectus", "presentation"];
const PERIOD_TYPES = ["annual", "quarterly", "interim"];

type ReportFormState = {
  company_id: string;
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
};

export function AdminReportsDashboard({
  companies,
  reports,
}: {
  companies: CompanyListItem[];
  reports: AdminReportSummary[];
}) {
  const [items, setItems] = useState(reports);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [form, setForm] = useState<ReportFormState>({
    company_id: companies[0]?.id ?? "",
    report_name: "",
    report_type: "q3",
    period_type: "quarterly",
    period_end_date: "",
    published_at: "",
    source_url: "",
    source_file_path: "",
    source_is_official: true,
    source_label: "Official filing source",
    ingestion_status: "draft",
    notes: "",
  });

  function handleCreateReport() {
    startTransition(async () => {
      setFeedback(null);
      const result = await createAdminReport({
        company_id: form.company_id,
        report_name: form.report_name,
        report_type: form.report_type,
        period_type: form.period_type,
        period_end_date: form.period_end_date,
        published_at: form.published_at || null,
        source_url: form.source_url || null,
        source_file_path: form.source_file_path || null,
        source_is_official: form.source_is_official,
        source_label: form.source_label || null,
        ingestion_status: form.ingestion_status,
        notes: form.notes || null,
      });

      if (!result.item) {
        setFeedback("Could not create report.");
        return;
      }

      setItems((current) => [
        {
          id: result.item.id,
          companyId: result.item.companyId,
          companyNameHe: result.item.companyNameHe,
          reportName: result.item.reportName,
          reportType: result.item.reportType,
          periodType: result.item.periodType,
          periodEndDate: result.item.periodEndDate,
          publishedAt: result.item.publishedAt,
          sourceUrl: result.item.sourceUrl,
          sourceFilePath: result.item.sourceFilePath,
          sourceIsOfficial: result.item.sourceIsOfficial,
          sourceLabel: result.item.sourceLabel,
          ingestionStatus: result.item.ingestionStatus,
          notes: result.item.notes,
          candidateCount: result.item.candidateCount,
          createdAt: result.item.createdAt,
          updatedAt: result.item.updatedAt,
        },
        ...current,
      ]);
      setFeedback("Report created.");
      setForm((current) => ({
        ...current,
        report_name: "",
        period_end_date: "",
        published_at: "",
        source_url: "",
        source_file_path: "",
        notes: "",
      }));
    });
  }

  return (
    <div className="section-stack">
      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Report Registry</p>
          <h2>Create report record</h2>
          <p className="panel-copy">
            Register a real source report first. Staging candidates attach to this record and only reach canonical tables through publish.
          </p>
        </div>

        {feedback ? <p className="muted-copy">{feedback}</p> : null}

        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Company</span>
            <select value={form.company_id} onChange={(event) => setForm((current) => ({ ...current, company_id: event.target.value }))}>
              {companies.length > 0 ? (
                companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.nameHe}
                  </option>
                ))
              ) : (
                <option value="">No companies available</option>
              )}
            </select>
          </label>
          <label className="filter-field">
            <span>Report name</span>
            <input value={form.report_name} onChange={(event) => setForm((current) => ({ ...current, report_name: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Report type</span>
            <select value={form.report_type} onChange={(event) => setForm((current) => ({ ...current, report_type: event.target.value }))}>
              {REPORT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Period type</span>
            <select value={form.period_type} onChange={(event) => setForm((current) => ({ ...current, period_type: event.target.value }))}>
              {PERIOD_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Period end date</span>
            <input type="date" value={form.period_end_date} onChange={(event) => setForm((current) => ({ ...current, period_end_date: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Published at</span>
            <input type="date" value={form.published_at} onChange={(event) => setForm((current) => ({ ...current, published_at: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Source URL</span>
            <input value={form.source_url} onChange={(event) => setForm((current) => ({ ...current, source_url: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Source file path / storage ref</span>
            <input value={form.source_file_path} onChange={(event) => setForm((current) => ({ ...current, source_file_path: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Source label</span>
            <input value={form.source_label} onChange={(event) => setForm((current) => ({ ...current, source_label: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Ingestion status</span>
            <select value={form.ingestion_status} onChange={(event) => setForm((current) => ({ ...current, ingestion_status: event.target.value }))}>
              <option value="draft">draft</option>
              <option value="ready_for_staging">ready_for_staging</option>
              <option value="in_review">in_review</option>
              <option value="published">published</option>
              <option value="rejected">rejected</option>
            </select>
          </label>
          <label className="panel-copy">
            <input checked={form.source_is_official} type="checkbox" onChange={(event) => setForm((current) => ({ ...current, source_is_official: event.target.checked }))} />{" "}
            Source is official
          </label>
          <label className="filter-field">
            <span>Notes</span>
            <textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
          </label>
        </div>

        <div className="form-actions">
          <button
            className="primary-button"
            disabled={isPending || !form.company_id || !form.report_name || !form.period_end_date}
            onClick={handleCreateReport}
            type="button"
          >
            Create report
          </button>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Reports</p>
          <h3>Registered reports</h3>
        </div>
        {items.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Report</th>
                  <th>Period end</th>
                  <th>Status</th>
                  <th>Candidates</th>
                </tr>
              </thead>
              <tbody>
                {items.map((report) => (
                  <tr key={report.id}>
                    <td>{report.companyNameHe}</td>
                    <td>
                      <a className="inline-link" href={`/admin/sources/${report.id}`}>
                        {report.reportName ?? "Unnamed report"}
                      </a>
                    </td>
                    <td>{formatDate(report.periodEndDate)}</td>
                    <td>{report.ingestionStatus}</td>
                    <td>{report.candidateCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No reports have been registered yet.</strong>
            <p className="panel-copy">Create the first report record above to start the manual ingestion workflow.</p>
          </div>
        )}
      </div>
    </div>
  );
}
