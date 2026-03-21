import type { ProjectListItem } from "@real-estat-map/shared";
import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";

const columns = [
  "Project",
  "Company",
  "City",
  "Type",
  "Status",
  "Known units",
  "Unsold",
] as const;

export function ProjectTable({
  rows,
  title = "Project table",
}: {
  rows?: ProjectListItem[] | null;
  title?: string;
}) {
  const safeRows = Array.isArray(rows) ? rows : [];

  return (
    <Panel
      eyebrow="Results"
      title={title}
      description="Latest public residential projects from the seeded database, with only source-backed values surfaced."
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
            {safeRows.length > 0 ? (
              safeRows.map((row) => (
                <tr key={row.projectId}>
                  <td>
                    <Link href={`/projects/${row.projectId}`}>{row.canonicalName}</Link>
                  </td>
                  <td>
                    <Link href={`/companies/${row.company.id}`}>{row.company?.nameHe ?? "Unknown company"}</Link>
                  </td>
                  <td>{row.city ?? "Unknown"}</td>
                  <td>
                    <div className="stacked-cell">
                      <span>{row.projectBusinessType}</span>
                      <Tag tone={row.locationQuality === "exact" ? "accent" : row.locationQuality === "unknown" ? "warning" : "default"}>
                        {row.locationQuality}
                      </Tag>
                    </div>
                  </td>
                  <td>{row.projectStatus ?? "Not disclosed"}</td>
                  <td>{row.marketedUnits ?? row.totalUnits ?? "Not disclosed"}</td>
                  <td>{row.unsoldUnits ?? "Not disclosed"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="empty-table">
                  No project rows are available right now. Try clearing filters or check that the API seed is loaded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
