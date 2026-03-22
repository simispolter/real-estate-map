import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { getAdminIntake } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AdminIntakePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const q = single(params.q);
  const { items, state } = await getAdminIntake({ q });

  return (
    <>
      <Panel
        eyebrow="Admin Intake"
        title="Project candidate review queue"
        description="This queue is centered on project candidates waiting for review, matching, and publish decisions. Sources support the work, but they are no longer the main frame."
      />

      {state === "error" ? (
        <Panel eyebrow="Status" title="Intake data is temporarily unavailable">
          <p className="panel-copy">The intake route is live, but the candidate queue could not be loaded right now.</p>
        </Panel>
      ) : null}

      <Panel eyebrow="Search" title="Candidate queue search">
        <form className="admin-form-grid" method="get">
          <label className="filter-field">
            <span>Search</span>
            <input defaultValue={q ?? ""} name="q" placeholder="Candidate, canonical match, company, city, source report" />
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              Search intake
            </button>
            <Link className="secondary-button" href="/admin/intake">
              Clear
            </Link>
          </div>
        </form>
      </Panel>

      <Panel eyebrow="Queue" title="Pending project candidates">
        {items.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Company</th>
                  <th>City</th>
                  <th>Source</th>
                  <th>Match</th>
                  <th>Confidence</th>
                  <th>Publish</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link href={`/admin/intake/${item.id}`}>{item.candidateProjectName}</Link>
                    </td>
                    <td>{item.company.nameHe}</td>
                    <td>{item.city ?? "Unknown"}</td>
                    <td>{item.sourceReportName ?? "Manual source"}</td>
                    <td>{item.matchedProjectName ?? item.matchingStatus}</td>
                    <td>{item.confidenceLevel}</td>
                    <td>{item.publishStatus}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No candidates are waiting in intake.</strong>
            <p className="panel-copy">
              {q
                ? "No candidates matched this search. Try a company, alias-adjacent project name, city, or report reference."
                : "Create candidates from Sources when a report is ready for manual review."}
            </p>
          </div>
        )}
      </Panel>
    </>
  );
}
