"use client";

import type { AdminExternalLayerDetail } from "@real-estat-map/shared";
import { useState, useTransition } from "react";

import { updateAdminLayer } from "@/lib/api";
import { formatDate } from "@/lib/format";

export function AdminLayerEditor({ layer }: { layer: AdminExternalLayerDetail }) {
  const [item, setItem] = useState(layer);
  const [form, setForm] = useState({
    layer_name: layer.layerName,
    source_name: layer.sourceName,
    source_url: layer.sourceUrl ?? "",
    geometry_type: layer.geometryType,
    update_cadence: layer.updateCadence,
    quality_score: layer.qualityScore?.toString() ?? "",
    visibility: layer.visibility,
    notes: layer.notes ?? "",
    is_active: layer.isActive,
    default_on_map: layer.defaultOnMap,
  });
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function setField(key: string, value: string | boolean) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSave() {
    startTransition(async () => {
      setFeedback(null);
      const result = await updateAdminLayer(item.id, {
        layer_name: form.layer_name,
        source_name: form.source_name,
        source_url: form.source_url || null,
        geometry_type: form.geometry_type,
        update_cadence: form.update_cadence,
        quality_score: form.quality_score ? Number(form.quality_score) : null,
        visibility: form.visibility,
        notes: form.notes || null,
        is_active: form.is_active,
        default_on_map: form.default_on_map,
      });
      if (!result.item) {
        setFeedback("Could not save layer.");
        return;
      }
      setItem(result.item);
      setFeedback("Layer updated.");
    });
  }

  return (
    <div className="section-stack">
      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Layer Registry</p>
          <h2>{item.layerName}</h2>
          <p className="panel-copy">
            {item.sourceName} | {item.recordCount} records | {item.relationCount} stored relations
          </p>
        </div>
        {feedback ? <p className="muted-copy">{feedback}</p> : null}
        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Layer name</span>
            <input value={form.layer_name} onChange={(event) => setField("layer_name", event.target.value)} />
          </label>
          <label className="filter-field">
            <span>Source name</span>
            <input value={form.source_name} onChange={(event) => setField("source_name", event.target.value)} />
          </label>
          <label className="filter-field">
            <span>Source URL</span>
            <input value={form.source_url} onChange={(event) => setField("source_url", event.target.value)} />
          </label>
          <label className="filter-field">
            <span>Geometry type</span>
            <select value={form.geometry_type} onChange={(event) => setField("geometry_type", event.target.value)}>
              {["point", "line", "polygon", "mixed"].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Update cadence</span>
            <select value={form.update_cadence} onChange={(event) => setField("update_cadence", event.target.value)}>
              {["ad_hoc", "daily", "weekly", "monthly", "quarterly", "annual"].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Quality score</span>
            <input value={form.quality_score} onChange={(event) => setField("quality_score", event.target.value)} />
          </label>
          <label className="filter-field">
            <span>Visibility</span>
            <select value={form.visibility} onChange={(event) => setField("visibility", event.target.value)}>
              {["public", "admin_only", "hidden"].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Notes</span>
            <textarea value={form.notes} onChange={(event) => setField("notes", event.target.value)} />
          </label>
        </div>
        <div className="tag-row">
          <label className="panel-copy">
            <input checked={form.is_active} onChange={(event) => setField("is_active", event.target.checked)} type="checkbox" /> Active
          </label>
          <label className="panel-copy">
            <input checked={form.default_on_map} onChange={(event) => setField("default_on_map", event.target.checked)} type="checkbox" /> Default on map
          </label>
          <span className="panel-copy">Last updated: {formatDate(item.updatedAt)}</span>
        </div>
        <div className="form-actions">
          <button className="primary-button" disabled={isPending} onClick={handleSave} type="button">
            Save layer
          </button>
        </div>
      </div>

      <div className="admin-grid">
        <div className="admin-form-card section-stack">
          <div>
            <p className="eyebrow">Records</p>
            <h3>Layer records</h3>
          </div>
          {item.records.length > 0 ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>City</th>
                    <th>External ID</th>
                    <th>Relations</th>
                  </tr>
                </thead>
                <tbody>
                  {item.records.map((record) => (
                    <tr key={record.id}>
                      <td>{record.label ?? "Unnamed"}</td>
                      <td>{record.city ?? "Unknown"}</td>
                      <td>{record.externalRecordId}</td>
                      <td>{record.relationCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <strong>No records are stored for this layer yet.</strong>
              <p className="panel-copy">The registry is ready for future ingestion even before records are loaded.</p>
            </div>
          )}
        </div>

        <div className="admin-form-card section-stack">
          <div>
            <p className="eyebrow">Relations</p>
            <h3>Future project linkage breakdown</h3>
          </div>
          {Object.keys(item.relationMethodBreakdown).length > 0 ? (
            <div className="tag-row">
              {Object.entries(item.relationMethodBreakdown).map(([key, value]) => (
                <span className="tag" key={key}>
                  {key}: {value}
                </span>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No external-project relations are stored yet.</strong>
              <p className="panel-copy">This layer is ready for future address-based, geometry-overlap, and manual linkage work.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
