import Link from "next/link";

import { AdminLayerCreatePanel } from "@/components/admin/admin-layer-create-panel";
import { Panel } from "@/components/ui/panel";
import { getAdminLayers } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function AdminLayersPage() {
  const { items, state } = await getAdminLayers();

  return (
    <>
      <Panel
        eyebrow="Admin Layers"
        title="External overlay registry"
        description="Manage external layers separately from canonical projects so future Tax Authority and open-data overlays can plug into a clean map framework."
      />

      <AdminLayerCreatePanel />

      {state === "error" ? (
        <Panel eyebrow="Status" title="Layer registry is temporarily unavailable">
          <p className="panel-copy">The map layer registry did not return a usable payload.</p>
        </Panel>
      ) : null}

      <Panel eyebrow="Registry" title="Available external layers">
        {items.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Layer</th>
                  <th>Source</th>
                  <th>Geometry</th>
                  <th>Visibility</th>
                  <th>Records</th>
                  <th>Relations</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link href={`/admin/layers/${item.id}`}>{item.layerName}</Link>
                    </td>
                    <td>{item.sourceName}</td>
                    <td>{item.geometryType}</td>
                    <td>{item.visibility}</td>
                    <td>{item.recordCount}</td>
                    <td>{item.relationCount}</td>
                    <td>{formatDate(item.updatedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No external layers are registered yet.</strong>
            <p className="panel-copy">Create the first registry entry here and it can immediately flow into the map layer framework.</p>
          </div>
        )}
      </Panel>
    </>
  );
}
