import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";
import { getAdminProjects } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function AdminProjectsPage() {
  const { items, state } = await getAdminProjects();

  return (
    <>
      <Panel
        eyebrow="Admin Projects"
        title="Project review queue"
        description="This is the first real internal correction surface: review a project, inspect provenance, adjust classification/location fields, and manage addresses with audit logging."
      >
        <div className="tag-row">
          <Tag>no auth yet</Tag>
          <Tag tone="warning">placeholder admin user</Tag>
        </div>
      </Panel>

      {state === "error" ? (
        <Panel eyebrow="Status" title="Admin project data is temporarily unavailable">
          <p className="panel-copy">The route is still alive, but the admin projects API did not return a usable payload.</p>
        </Panel>
      ) : null}

      <Panel eyebrow="Review Queue" title="Projects awaiting review">
        {items.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Company</th>
                  <th>City</th>
                  <th>Business type</th>
                  <th>Permit</th>
                  <th>Latest snapshot</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link href={`/admin/projects/${item.id}`}>{item.canonicalName}</Link>
                    </td>
                    <td>{item.company.nameHe}</td>
                    <td>{item.city ?? "Unknown"}</td>
                    <td>
                      <div className="stacked-cell">
                        <span>{item.projectBusinessType}</span>
                        {item.needsAdminReview ? <Tag tone="warning">review requested</Tag> : <Tag>ready</Tag>}
                      </div>
                    </td>
                    <td>{item.permitStatus ?? "Not disclosed"}</td>
                    <td>{formatDate(item.latestSnapshotDate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No admin project rows are available.</strong>
            <p className="panel-copy">Seed data may not be loaded yet, or the current review queue is empty.</p>
          </div>
        )}
      </Panel>
    </>
  );
}
