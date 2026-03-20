import type { PlaceholderProjectRow } from "@real-estat-map/shared";

import { Panel } from "@/components/ui/panel";

const columns = [
  "Project",
  "Company",
  "City",
  "Type",
  "Status",
  "Location confidence",
] as const;

export function ProjectTable({
  rows,
  title = "Project table",
}: {
  rows: PlaceholderProjectRow[];
  title?: string;
}) {
  return (
    <Panel
      eyebrow="Results"
      title={title}
      description="The table structure is live now, while data binding is deferred until public API endpoints start reading the canonical database."
    >
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length > 0 ? (
              rows.map((row) => (
                <tr key={`${row.companyName}-${row.canonicalName}`}>
                  <td>{row.canonicalName}</td>
                  <td>{row.companyName}</td>
                  <td>{row.city}</td>
                  <td>{row.projectBusinessType}</td>
                  <td>{row.status}</td>
                  <td>{row.locationConfidence}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="empty-table">
                  No public project rows yet. This surface is waiting for published snapshots from the
                  FastAPI backend.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
