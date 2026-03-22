"use client";

import { useState, useTransition } from "react";

import { createAdminLayer } from "@/lib/api";

export function AdminLayerCreatePanel() {
  const [form, setForm] = useState({
    layer_name: "",
    source_name: "",
    source_url: "",
    geometry_type: "point",
    update_cadence: "ad_hoc",
    quality_score: "",
    visibility: "public",
    notes: "",
    is_active: true,
    default_on_map: false,
  });
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function setField(key: string, value: string | boolean) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit() {
    startTransition(async () => {
      setFeedback(null);
      const result = await createAdminLayer({
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
        setFeedback("Could not create layer.");
        return;
      }
      window.location.href = `/admin/layers/${result.item.id}`;
    });
  }

  return (
    <div className="admin-form-card section-stack">
      <div>
        <p className="eyebrow">Create Layer</p>
        <h3>External overlay registry entry</h3>
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
      </div>
      <div className="form-actions">
        <button className="primary-button" disabled={isPending || !form.layer_name || !form.source_name} onClick={handleSubmit} type="button">
          Create layer
        </button>
      </div>
    </div>
  );
}
