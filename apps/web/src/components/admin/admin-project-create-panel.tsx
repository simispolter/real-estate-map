"use client";

import type { CompanyListItem } from "@real-estat-map/shared";
import {
  GOVERNMENT_PROGRAM_TYPES,
  LOCATION_CONFIDENCE_LEVELS,
  PROJECT_DISCLOSURE_LEVELS,
  PROJECT_BUSINESS_TYPES,
  PROJECT_LIFECYCLE_STAGES,
  URBAN_RENEWAL_TYPES,
} from "@real-estat-map/shared";
import { useState, useTransition } from "react";

import { createAdminProject } from "@/lib/api";
import { formatDisclosureLevelLabel, formatLifecycleStageLabel } from "@/lib/format";

type Props = {
  companies: CompanyListItem[];
};

type FormState = {
  canonical_name: string;
  company_id: string;
  city: string;
  neighborhood: string;
  lifecycle_stage: string;
  disclosure_level: string;
  project_business_type: string;
  government_program_type: string;
  project_urban_renewal_type: string;
  location_confidence: string;
  is_publicly_visible: boolean;
  source_conflict_flag: boolean;
  notes_internal: string;
  reviewer_note: string;
};

export function AdminProjectCreatePanel({ companies }: Props) {
  const [form, setForm] = useState<FormState>({
    canonical_name: "",
    company_id: companies[0]?.id ?? "",
    city: "",
    neighborhood: "",
    lifecycle_stage: "",
    disclosure_level: "",
    project_business_type: "regular_dev",
    government_program_type: "none",
    project_urban_renewal_type: "none",
    location_confidence: "city_only",
    is_publicly_visible: false,
    source_conflict_flag: false,
    notes_internal: "",
    reviewer_note: "",
  });
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit() {
    startTransition(async () => {
      setFeedback(null);
      const result = await createAdminProject({
        canonical_name: form.canonical_name,
        company_id: form.company_id,
        city: form.city || null,
        neighborhood: form.neighborhood || null,
        lifecycle_stage: form.lifecycle_stage || null,
        disclosure_level: form.disclosure_level || null,
        project_business_type: form.project_business_type,
        government_program_type: form.project_business_type === "govt_program" ? form.government_program_type : "none",
        project_urban_renewal_type:
          form.project_business_type === "urban_renewal" ? form.project_urban_renewal_type : "none",
        location_confidence: form.location_confidence,
        is_publicly_visible: form.is_publicly_visible,
        source_conflict_flag: form.source_conflict_flag,
        notes_internal: form.notes_internal || null,
        reviewer_note: form.reviewer_note || null,
        value_origin_type: "manual",
      });

      if (!result.item) {
        setFeedback("Could not create project.");
        return;
      }

      window.location.href = `/admin/projects/${result.item.id}`;
    });
  }

  return (
    <div className="admin-form-card section-stack">
      <div>
        <p className="eyebrow">Create Project</p>
        <h3>Manual canonical entry</h3>
        <p className="panel-copy">
          Create a canonical project directly. After save, you can add addresses, aliases, and the first snapshot.
        </p>
      </div>

      {feedback ? <p className="muted-copy">{feedback}</p> : null}

      <div className="admin-form-grid">
        <label className="filter-field">
          <span>Canonical name</span>
          <input value={form.canonical_name} onChange={(event) => setField("canonical_name", event.target.value)} />
        </label>
        <label className="filter-field">
          <span>Company</span>
          <select value={form.company_id} onChange={(event) => setField("company_id", event.target.value)}>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.nameHe}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>City</span>
          <input value={form.city} onChange={(event) => setField("city", event.target.value)} />
        </label>
        <label className="filter-field">
          <span>Neighborhood</span>
          <input value={form.neighborhood} onChange={(event) => setField("neighborhood", event.target.value)} />
        </label>
        <label className="filter-field">
          <span>Lifecycle stage</span>
          <select value={form.lifecycle_stage} onChange={(event) => setField("lifecycle_stage", event.target.value)}>
            <option value="">Not set</option>
            {PROJECT_LIFECYCLE_STAGES.map((value) => (
              <option key={value} value={value}>
                {formatLifecycleStageLabel(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Disclosure level</span>
          <select value={form.disclosure_level} onChange={(event) => setField("disclosure_level", event.target.value)}>
            <option value="">Not set</option>
            {PROJECT_DISCLOSURE_LEVELS.map((value) => (
              <option key={value} value={value}>
                {formatDisclosureLevelLabel(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Business type</span>
          <select value={form.project_business_type} onChange={(event) => setField("project_business_type", event.target.value)}>
            {PROJECT_BUSINESS_TYPES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Government program</span>
          <select value={form.government_program_type} onChange={(event) => setField("government_program_type", event.target.value)}>
            {GOVERNMENT_PROGRAM_TYPES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Urban renewal</span>
          <select value={form.project_urban_renewal_type} onChange={(event) => setField("project_urban_renewal_type", event.target.value)}>
            {URBAN_RENEWAL_TYPES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Location confidence</span>
          <select value={form.location_confidence} onChange={(event) => setField("location_confidence", event.target.value)}>
            {LOCATION_CONFIDENCE_LEVELS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Internal note</span>
          <textarea value={form.notes_internal} onChange={(event) => setField("notes_internal", event.target.value)} />
        </label>
        <label className="filter-field">
          <span>Reviewer note</span>
          <input value={form.reviewer_note} onChange={(event) => setField("reviewer_note", event.target.value)} />
        </label>
      </div>

      <div className="tag-row">
        <label className="panel-copy">
          <input
            checked={form.is_publicly_visible}
            type="checkbox"
            onChange={(event) => setField("is_publicly_visible", event.target.checked)}
          />{" "}
          Publicly visible
        </label>
        <label className="panel-copy">
          <input
            checked={form.source_conflict_flag}
            type="checkbox"
            onChange={(event) => setField("source_conflict_flag", event.target.checked)}
          />{" "}
          Source conflict flag
        </label>
      </div>

      <div className="form-actions">
        <button
          className="primary-button"
          disabled={isPending || !form.canonical_name.trim() || !form.company_id}
          onClick={handleSubmit}
          type="button"
        >
          Create canonical project
        </button>
      </div>
    </div>
  );
}
