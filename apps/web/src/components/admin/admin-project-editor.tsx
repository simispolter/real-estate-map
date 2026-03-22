"use client";

import type { AdminProjectDetail, CompanyListItem, ProjectAddress } from "@real-estat-map/shared";
import {
  GOVERNMENT_PROGRAM_TYPES,
  LOCATION_CONFIDENCE_LEVELS,
  PERMIT_STATUSES,
  PROJECT_BUSINESS_TYPES,
  PROJECT_STATUSES,
  URBAN_RENEWAL_TYPES,
  VALUE_ORIGIN_TYPES,
} from "@real-estat-map/shared";
import Link from "next/link";
import { useState, useTransition } from "react";

import {
  addAdminProjectAlias,
  createAdminProjectSnapshot,
  deleteAdminProjectAddress,
  deleteAdminProjectAlias,
  geocodeAdminProjectAddress,
  normalizeAdminProjectAddress,
  updateAdminProject,
  updateAdminProjectDisplayGeometry,
  updateAdminSnapshot,
  upsertAdminProjectAddress,
} from "@/lib/api";
import { formatAddressLabel, formatCurrency, formatDate, formatNumber, formatPercent } from "@/lib/format";

type Props = {
  project: AdminProjectDetail;
  companies: CompanyListItem[];
};

type ProjectFormState = {
  canonical_name: string;
  company_id: string;
  city: string;
  neighborhood: string;
  project_business_type: string;
  government_program_type: string;
  project_urban_renewal_type: string;
  permit_status: string;
  project_status: string;
  location_confidence: string;
  is_publicly_visible: boolean;
  source_conflict_flag: boolean;
  notes_internal: string;
  change_reason: string;
};

type AliasFormState = {
  alias_name: string;
  value_origin_type: string;
  alias_source_type: string;
  source_report_id: string;
  is_active: boolean;
  notes: string;
  make_preferred: boolean;
  reviewer_note: string;
};

type AddressDraft = {
  address_text_raw: string;
  street: string;
  house_number_from: string;
  house_number_to: string;
  city: string;
  lat: string;
  lng: string;
  location_confidence: string;
  is_primary: boolean;
  normalized_display_address: string;
  geocoding_method: string;
  geocoding_source_label: string;
  value_origin_type: string;
  change_reason: string;
};

type SnapshotFormState = {
  snapshot_id: string;
  report_id: string;
  snapshot_date: string;
  total_units: string;
  marketed_units: string;
  sold_units_cumulative: string;
  unsold_units: string;
  avg_price_per_sqm_cumulative: string;
  gross_profit_total_expected: string;
  gross_margin_expected_pct: string;
  permit_status: string;
  project_status: string;
  notes_internal: string;
  value_origin_type: string;
  confidence_level: string;
  reviewer_note: string;
};

type DisplayGeometryFormState = {
  geometry_type: string;
  geometry_source: string;
  location_confidence: string;
  center_lat: string;
  center_lng: string;
  address_summary: string;
  note: string;
  geometry_geojson: string;
  change_reason: string;
};

function buildProjectForm(project: AdminProjectDetail): ProjectFormState {
  return {
    canonical_name: project.canonicalName,
    company_id: project.company.id,
    city: project.location.city ?? "",
    neighborhood: project.location.neighborhood ?? "",
    project_business_type: project.classification.projectBusinessType,
    government_program_type: project.classification.governmentProgramType,
    project_urban_renewal_type: project.classification.projectUrbanRenewalType,
    permit_status: project.classification.permitStatus ?? "",
    project_status: project.classification.projectStatus ?? "",
    location_confidence: project.location.locationConfidence,
    is_publicly_visible: project.isPubliclyVisible,
    source_conflict_flag: project.sourceConflictFlag,
    notes_internal: project.notesInternal ?? "",
    change_reason: "",
  };
}

function buildAddressDraft(address: ProjectAddress): AddressDraft {
  return {
    address_text_raw: address.addressTextRaw ?? "",
    street: address.street ?? "",
    house_number_from: address.houseNumberFrom?.toString() ?? "",
    house_number_to: address.houseNumberTo?.toString() ?? "",
    city: address.city ?? "",
    lat: address.lat?.toString() ?? "",
    lng: address.lng?.toString() ?? "",
    location_confidence: address.locationConfidence,
    is_primary: address.isPrimary,
    normalized_display_address: address.normalizedDisplayAddress ?? "",
    geocoding_method: address.geocodingMethod ?? "",
    geocoding_source_label: address.geocodingSourceLabel ?? "",
    value_origin_type: address.valueOriginType,
    change_reason: "",
  };
}

function emptyAddressDraft(city: string | null): AddressDraft {
  return {
    address_text_raw: "",
    street: "",
    house_number_from: "",
    house_number_to: "",
    city: city ?? "",
    lat: "",
    lng: "",
    location_confidence: "city_only",
    is_primary: false,
    normalized_display_address: "",
    geocoding_method: "",
    geocoding_source_label: "",
    value_origin_type: "manual",
    change_reason: "",
  };
}

function buildDisplayGeometryForm(project: AdminProjectDetail): DisplayGeometryFormState {
  return {
    geometry_type: project.displayGeometry.geometryType,
    geometry_source: project.displayGeometry.geometrySource,
    location_confidence: project.displayGeometry.locationConfidence,
    center_lat: project.displayGeometry.centerLat?.toString() ?? "",
    center_lng: project.displayGeometry.centerLng?.toString() ?? "",
    address_summary: project.displayGeometry.addressSummary ?? "",
    note: project.displayGeometry.note ?? "",
    geometry_geojson: project.displayGeometry.geometryGeojson
      ? JSON.stringify(project.displayGeometry.geometryGeojson, null, 2)
      : "",
    change_reason: "",
  };
}

function buildSnapshotForm(project: AdminProjectDetail): SnapshotFormState {
  const latest = project.latestSnapshot;
  return {
    snapshot_id: "",
    report_id: "",
    snapshot_date: latest?.snapshotDate ?? "",
    total_units: latest?.totalUnits?.toString() ?? "",
    marketed_units: latest?.marketedUnits?.toString() ?? "",
    sold_units_cumulative: latest?.soldUnitsCumulative?.toString() ?? "",
    unsold_units: latest?.unsoldUnits?.toString() ?? "",
    avg_price_per_sqm_cumulative: latest?.avgPricePerSqmCumulative?.toString() ?? "",
    gross_profit_total_expected: latest?.grossProfitTotalExpected?.toString() ?? "",
    gross_margin_expected_pct: latest?.grossMarginExpectedPct?.toString() ?? "",
    permit_status: latest?.permitStatus ?? "",
    project_status: latest?.projectStatus ?? "",
    notes_internal: "",
    value_origin_type: "manual",
    confidence_level: "medium",
    reviewer_note: "",
  };
}

function toNullableNumber(value: string) {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildAddressPayload(draft: AddressDraft) {
  return {
    address_text_raw: draft.address_text_raw || null,
    street: draft.street || null,
    house_number_from: toNullableNumber(draft.house_number_from),
    house_number_to: toNullableNumber(draft.house_number_to),
    city: draft.city || null,
    lat: toNullableNumber(draft.lat),
    lng: toNullableNumber(draft.lng),
    location_confidence: draft.location_confidence,
    is_primary: draft.is_primary,
    normalized_display_address: draft.normalized_display_address || null,
    geocoding_method: draft.geocoding_method || null,
    geocoding_source_label: draft.geocoding_source_label || null,
    value_origin_type: draft.value_origin_type,
    change_reason: draft.change_reason || null,
  };
}

function buildSnapshotPayload(form: SnapshotFormState) {
  return {
    report_id: form.report_id || null,
    snapshot_date: form.snapshot_date,
    total_units: toNullableNumber(form.total_units),
    marketed_units: toNullableNumber(form.marketed_units),
    sold_units_cumulative: toNullableNumber(form.sold_units_cumulative),
    unsold_units: toNullableNumber(form.unsold_units),
    avg_price_per_sqm_cumulative: toNullableNumber(form.avg_price_per_sqm_cumulative),
    gross_profit_total_expected: toNullableNumber(form.gross_profit_total_expected),
    gross_margin_expected_pct: toNullableNumber(form.gross_margin_expected_pct),
    permit_status: form.permit_status || null,
    project_status: form.project_status || null,
    notes_internal: form.notes_internal || null,
    value_origin_type: form.value_origin_type,
    confidence_level: form.confidence_level,
    reviewer_note: form.reviewer_note || null,
  };
}

export function AdminProjectEditor({ companies, project }: Props) {
  const [item, setItem] = useState(project);
  const [projectForm, setProjectForm] = useState<ProjectFormState>(() => buildProjectForm(project));
  const [aliasForm, setAliasForm] = useState<AliasFormState>({
    alias_name: "",
    value_origin_type: "manual",
    alias_source_type: "manual",
    source_report_id: "",
    is_active: true,
    notes: "",
    make_preferred: false,
    reviewer_note: "",
  });
  const [addressDrafts, setAddressDrafts] = useState<Record<string, AddressDraft>>(
    Object.fromEntries(project.addresses.map((address) => [address.id, buildAddressDraft(address)])),
  );
  const [newAddressDraft, setNewAddressDraft] = useState<AddressDraft>(() => emptyAddressDraft(project.location.city));
  const [displayGeometryForm, setDisplayGeometryForm] = useState<DisplayGeometryFormState>(() =>
    buildDisplayGeometryForm(project),
  );
  const [snapshotForm, setSnapshotForm] = useState<SnapshotFormState>(() => buildSnapshotForm(project));
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function syncProject(nextProject: AdminProjectDetail) {
    setItem(nextProject);
    setProjectForm(buildProjectForm(nextProject));
    setAddressDrafts(Object.fromEntries(nextProject.addresses.map((address) => [address.id, buildAddressDraft(address)])));
    setNewAddressDraft(emptyAddressDraft(nextProject.location.city));
    setDisplayGeometryForm(buildDisplayGeometryForm(nextProject));
    setSnapshotForm(buildSnapshotForm(nextProject));
  }

  function handleSaveProject() {
    startTransition(async () => {
      setFeedback(null);
      const result = await updateAdminProject(item.id, {
        canonical_name: projectForm.canonical_name,
        company_id: projectForm.company_id,
        city: projectForm.city || null,
        neighborhood: projectForm.neighborhood || null,
        project_business_type: projectForm.project_business_type,
        government_program_type:
          projectForm.project_business_type === "govt_program" ? projectForm.government_program_type : "none",
        project_urban_renewal_type:
          projectForm.project_business_type === "urban_renewal" ? projectForm.project_urban_renewal_type : "none",
        permit_status: projectForm.permit_status || null,
        project_status: projectForm.project_status || null,
        location_confidence: projectForm.location_confidence,
        is_publicly_visible: projectForm.is_publicly_visible,
        source_conflict_flag: projectForm.source_conflict_flag,
        notes_internal: projectForm.notes_internal || null,
        field_origin_types: {
          canonical_name: "manual",
          company_id: "manual",
          city: "manual",
          neighborhood: "manual",
          project_business_type: "manual",
          government_program_type: "manual",
          project_urban_renewal_type: "manual",
          permit_status: "manual",
          project_status: "manual",
          location_confidence: "manual",
        },
        change_reason: projectForm.change_reason || null,
      });
      if (!result.item) {
        setFeedback("Could not save canonical project changes.");
        return;
      }
      syncProject(result.item);
      setFeedback("Canonical project updated.");
    });
  }

  function handleAddAlias() {
    startTransition(async () => {
      setFeedback(null);
      const result = await addAdminProjectAlias(item.id, {
        alias_name: aliasForm.alias_name,
        value_origin_type: aliasForm.value_origin_type,
        alias_source_type: aliasForm.alias_source_type,
        source_report_id: aliasForm.source_report_id || null,
        is_active: aliasForm.is_active,
        notes: aliasForm.notes || null,
        make_preferred: aliasForm.make_preferred,
        reviewer_note: aliasForm.reviewer_note || null,
      });
      if (!result.item) {
        setFeedback("Could not save alias.");
        return;
      }
      syncProject(result.item);
      setAliasForm({
        alias_name: "",
        value_origin_type: "manual",
        alias_source_type: "manual",
        source_report_id: "",
        is_active: true,
        notes: "",
        make_preferred: false,
        reviewer_note: "",
      });
      setFeedback("Alias saved.");
    });
  }

  function handleRemoveAlias(aliasId: string) {
    startTransition(async () => {
      setFeedback(null);
      const result = await deleteAdminProjectAlias(item.id, aliasId, "Removed from project-first admin");
      if (!result.item) {
        setFeedback("Could not remove alias.");
        return;
      }
      syncProject(result.item);
      setFeedback("Alias removed.");
    });
  }

  function saveAddress(addressId?: string) {
    const draft = addressId ? addressDrafts[addressId] : newAddressDraft;
    if (!draft) {
      return;
    }
    startTransition(async () => {
      setFeedback(null);
      const result = await upsertAdminProjectAddress(item.id, buildAddressPayload(draft), addressId);
      if (!result.item) {
        setFeedback("Could not save address.");
        return;
      }
      syncProject(result.item);
      setFeedback(addressId ? "Address updated." : "Address added.");
    });
  }

  function removeAddress(addressId: string) {
    startTransition(async () => {
      setFeedback(null);
      const result = await deleteAdminProjectAddress(item.id, addressId);
      if (!result.item) {
        setFeedback("Could not remove address.");
        return;
      }
      syncProject(result.item);
      setFeedback("Address removed.");
    });
  }

  function normalizeAddress(addressId: string) {
    startTransition(async () => {
      setFeedback(null);
      const result = await normalizeAdminProjectAddress(item.id, addressId);
      if (!result.item) {
        setFeedback("Could not normalize address.");
        return;
      }
      syncProject(result.item);
      setFeedback("Address normalized.");
    });
  }

  function geocodeAddress(addressId: string) {
    startTransition(async () => {
      setFeedback(null);
      const result = await geocodeAdminProjectAddress(item.id, addressId);
      if (!result.item) {
        setFeedback("Could not geocode address.");
        return;
      }
      syncProject(result.item);
      setFeedback("Address geocoded.");
    });
  }

  function saveDisplayGeometry() {
    startTransition(async () => {
      setFeedback(null);
      let geometryGeojson: Record<string, unknown> | null = null;
      if (displayGeometryForm.geometry_geojson.trim()) {
        try {
          const parsed = JSON.parse(displayGeometryForm.geometry_geojson);
          geometryGeojson = parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : null;
        } catch {
          setFeedback("Display geometry JSON is invalid.");
          return;
        }
      }

      const result = await updateAdminProjectDisplayGeometry(item.id, {
        geometry_type: displayGeometryForm.geometry_type,
        geometry_source: displayGeometryForm.geometry_source,
        location_confidence: displayGeometryForm.location_confidence,
        center_lat: toNullableNumber(displayGeometryForm.center_lat),
        center_lng: toNullableNumber(displayGeometryForm.center_lng),
        address_summary: displayGeometryForm.address_summary || null,
        note: displayGeometryForm.note || null,
        geometry_geojson: geometryGeojson,
        change_reason: displayGeometryForm.change_reason || null,
      });
      if (!result.item) {
        setFeedback("Could not update display geometry.");
        return;
      }
      syncProject(result.item);
      setFeedback("Display geometry updated.");
    });
  }

  function loadSnapshot(snapshotId: string) {
    const snapshot = item.snapshots.find((entry) => entry.id === snapshotId);
    if (!snapshot) {
      return;
    }
    setSnapshotForm({
      snapshot_id: snapshot.id,
      report_id: snapshot.reportId,
      snapshot_date: snapshot.snapshotDate,
      total_units: snapshot.totalUnits?.toString() ?? "",
      marketed_units: snapshot.marketedUnits?.toString() ?? "",
      sold_units_cumulative: snapshot.soldUnitsCumulative?.toString() ?? "",
      unsold_units: snapshot.unsoldUnits?.toString() ?? "",
      avg_price_per_sqm_cumulative: snapshot.avgPricePerSqmCumulative?.toString() ?? "",
      gross_profit_total_expected: snapshot.grossProfitTotalExpected?.toString() ?? "",
      gross_margin_expected_pct: snapshot.grossMarginExpectedPct?.toString() ?? "",
      permit_status: snapshot.permitStatus ?? "",
      project_status: snapshot.projectStatus ?? "",
      notes_internal: snapshot.notesInternal ?? "",
      value_origin_type: "manual",
      confidence_level: "medium",
      reviewer_note: "",
    });
  }

  function handleSaveSnapshot() {
    startTransition(async () => {
      setFeedback(null);
      const payload = buildSnapshotPayload(snapshotForm);
      const result = snapshotForm.snapshot_id
        ? await updateAdminSnapshot(snapshotForm.snapshot_id, payload)
        : await createAdminProjectSnapshot(item.id, payload);
      if (!result.item) {
        setFeedback("Could not save snapshot.");
        return;
      }
      syncProject(result.item);
      setFeedback(snapshotForm.snapshot_id ? "Snapshot updated." : "Snapshot created.");
    });
  }

  return (
    <div className="section-stack">
      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Canonical Project</p>
          <h2>{item.canonicalName}</h2>
          <p className="panel-copy">
            {item.company.nameHe} | {item.isPubliclyVisible ? "public" : "internal"} | {item.snapshots.length} snapshots
          </p>
        </div>
        {feedback ? <p className="muted-copy">{feedback}</p> : null}
        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Canonical name</span>
            <input value={projectForm.canonical_name} onChange={(event) => setProjectForm((current) => ({ ...current, canonical_name: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Company</span>
            <select value={projectForm.company_id} onChange={(event) => setProjectForm((current) => ({ ...current, company_id: event.target.value }))}>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.nameHe}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>City</span>
            <input value={projectForm.city} onChange={(event) => setProjectForm((current) => ({ ...current, city: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Neighborhood</span>
            <input value={projectForm.neighborhood} onChange={(event) => setProjectForm((current) => ({ ...current, neighborhood: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Business type</span>
            <select value={projectForm.project_business_type} onChange={(event) => setProjectForm((current) => ({ ...current, project_business_type: event.target.value }))}>
              {PROJECT_BUSINESS_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Government program</span>
            <select value={projectForm.government_program_type} onChange={(event) => setProjectForm((current) => ({ ...current, government_program_type: event.target.value }))}>
              {GOVERNMENT_PROGRAM_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Urban renewal</span>
            <select value={projectForm.project_urban_renewal_type} onChange={(event) => setProjectForm((current) => ({ ...current, project_urban_renewal_type: event.target.value }))}>
              {URBAN_RENEWAL_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Permit status</span>
            <select value={projectForm.permit_status} onChange={(event) => setProjectForm((current) => ({ ...current, permit_status: event.target.value }))}>
              <option value="">Not disclosed</option>
              {PERMIT_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Project status</span>
            <select value={projectForm.project_status} onChange={(event) => setProjectForm((current) => ({ ...current, project_status: event.target.value }))}>
              <option value="">Not disclosed</option>
              {PROJECT_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Location confidence</span>
            <select value={projectForm.location_confidence} onChange={(event) => setProjectForm((current) => ({ ...current, location_confidence: event.target.value }))}>
              {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Internal note</span>
            <textarea value={projectForm.notes_internal} onChange={(event) => setProjectForm((current) => ({ ...current, notes_internal: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Change reason</span>
            <input value={projectForm.change_reason} onChange={(event) => setProjectForm((current) => ({ ...current, change_reason: event.target.value }))} />
          </label>
        </div>
        <div className="tag-row">
          <label className="panel-copy">
            <input checked={projectForm.is_publicly_visible} type="checkbox" onChange={(event) => setProjectForm((current) => ({ ...current, is_publicly_visible: event.target.checked }))} /> Publicly visible
          </label>
          <label className="panel-copy">
            <input checked={projectForm.source_conflict_flag} type="checkbox" onChange={(event) => setProjectForm((current) => ({ ...current, source_conflict_flag: event.target.checked }))} /> Source conflict flag
          </label>
        </div>
        <div className="form-actions">
          <button className="primary-button" disabled={isPending} onClick={handleSaveProject} type="button">
            Save canonical project
          </button>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Aliases</p>
          <h3>Canonical naming history</h3>
        </div>
        {item.aliases.length > 0 ? (
          <div className="section-stack">
            {item.aliases.map((alias) => (
              <div className="candidate-suggestion-card" key={alias.id}>
                <div>
                  <strong>{alias.aliasName}</strong>
                  <p className="panel-copy">
                    {[alias.valueOriginType, alias.aliasSourceType, alias.isActive ? "active" : "inactive"].join(" | ")}
                  </p>
                  {alias.sourceReportId ? <p className="muted-copy">source report {alias.sourceReportId}</p> : null}
                </div>
                <div className="form-actions">
                  <button className="secondary-button" disabled={isPending} onClick={() => handleRemoveAlias(alias.id)} type="button">
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>No aliases yet.</strong>
            <p className="panel-copy">Add alternate naming so future candidate matching has more context.</p>
          </div>
        )}
        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Alias name</span>
            <input value={aliasForm.alias_name} onChange={(event) => setAliasForm((current) => ({ ...current, alias_name: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Origin</span>
            <select value={aliasForm.value_origin_type} onChange={(event) => setAliasForm((current) => ({ ...current, value_origin_type: event.target.value }))}>
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Alias source type</span>
            <select value={aliasForm.alias_source_type} onChange={(event) => setAliasForm((current) => ({ ...current, alias_source_type: event.target.value }))}>
              <option value="manual">manual</option>
              <option value="source">source</option>
              <option value="system">system</option>
            </select>
          </label>
          <label className="filter-field">
            <span>Source report ID</span>
            <input value={aliasForm.source_report_id} onChange={(event) => setAliasForm((current) => ({ ...current, source_report_id: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Notes</span>
            <input value={aliasForm.notes} onChange={(event) => setAliasForm((current) => ({ ...current, notes: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Reviewer note</span>
            <input value={aliasForm.reviewer_note} onChange={(event) => setAliasForm((current) => ({ ...current, reviewer_note: event.target.value }))} />
          </label>
        </div>
        <label className="panel-copy">
          <input checked={aliasForm.make_preferred} type="checkbox" onChange={(event) => setAliasForm((current) => ({ ...current, make_preferred: event.target.checked }))} /> Promote this alias to preferred canonical name
        </label>
        <label className="panel-copy">
          <input checked={aliasForm.is_active} type="checkbox" onChange={(event) => setAliasForm((current) => ({ ...current, is_active: event.target.checked }))} /> Alias is active for matching
        </label>
        <div className="form-actions">
          <button className="primary-button" disabled={isPending || !aliasForm.alias_name.trim()} onClick={handleAddAlias} type="button">
            Save alias
          </button>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Spatial Model</p>
          <h3>Primary display geometry</h3>
          <p className="panel-copy">
            This is the geometry the public map surface uses first. Address normalization and geocoding can update it, or you can override it manually here.
          </p>
        </div>
        <div className="detail-list">
          <div>
            <strong>Current geometry type</strong>
            <p className="panel-copy">{item.displayGeometry.geometryType}</p>
          </div>
          <div>
            <strong>Geometry source</strong>
            <p className="panel-copy">{item.displayGeometry.geometrySource}</p>
          </div>
          <div>
            <strong>Location quality</strong>
            <p className="panel-copy">{item.displayGeometry.locationQuality}</p>
          </div>
          <div>
            <strong>Address summary</strong>
            <p className="panel-copy">{item.displayGeometry.addressSummary ?? "Not disclosed"}</p>
          </div>
        </div>
        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Geometry type</span>
            <select
              value={displayGeometryForm.geometry_type}
              onChange={(event) =>
                setDisplayGeometryForm((current) => ({ ...current, geometry_type: event.target.value }))
              }
            >
              {["exact_point", "approximate_point", "address_range", "polygon", "area", "city_centroid", "unknown"].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Geometry source</span>
            <select
              value={displayGeometryForm.geometry_source}
              onChange={(event) =>
                setDisplayGeometryForm((current) => ({ ...current, geometry_source: event.target.value }))
              }
            >
              {["manual_override", "reported", "geocoded", "city_registry", "inferred", "unknown"].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Location confidence</span>
            <select
              value={displayGeometryForm.location_confidence}
              onChange={(event) =>
                setDisplayGeometryForm((current) => ({ ...current, location_confidence: event.target.value }))
              }
            >
              {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Center latitude</span>
            <input
              value={displayGeometryForm.center_lat}
              onChange={(event) => setDisplayGeometryForm((current) => ({ ...current, center_lat: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Center longitude</span>
            <input
              value={displayGeometryForm.center_lng}
              onChange={(event) => setDisplayGeometryForm((current) => ({ ...current, center_lng: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Address summary</span>
            <input
              value={displayGeometryForm.address_summary}
              onChange={(event) =>
                setDisplayGeometryForm((current) => ({ ...current, address_summary: event.target.value }))
              }
            />
          </label>
          <label className="filter-field">
            <span>Override note</span>
            <input
              value={displayGeometryForm.note}
              onChange={(event) => setDisplayGeometryForm((current) => ({ ...current, note: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Change reason</span>
            <input
              value={displayGeometryForm.change_reason}
              onChange={(event) =>
                setDisplayGeometryForm((current) => ({ ...current, change_reason: event.target.value }))
              }
            />
          </label>
          <label className="filter-field">
            <span>Geometry GeoJSON (optional)</span>
            <textarea
              value={displayGeometryForm.geometry_geojson}
              onChange={(event) =>
                setDisplayGeometryForm((current) => ({ ...current, geometry_geojson: event.target.value }))
              }
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="primary-button" disabled={isPending} onClick={saveDisplayGeometry} type="button">
            Save display geometry
          </button>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Snapshots</p>
          <h3>Project history over time</h3>
        </div>
        {item.snapshots.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Units</th>
                  <th>Avg sqm</th>
                  <th>Margin</th>
                  <th>Source</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {item.snapshots.map((snapshot) => (
                  <tr key={snapshot.id}>
                    <td>{formatDate(snapshot.snapshotDate)}</td>
                    <td>{snapshot.projectStatus ?? snapshot.permitStatus ?? "Unknown"}</td>
                    <td>{formatNumber(snapshot.totalUnits)}</td>
                    <td>{formatCurrency(snapshot.avgPricePerSqmCumulative)}</td>
                    <td>{formatPercent(snapshot.grossMarginExpectedPct)}</td>
                    <td>
                      <div className="stacked-cell">
                        <span>{snapshot.reportName ?? "Manual source"}</span>
                        <span className="muted-copy">
                          {snapshot.chronologyStatus}
                          {snapshot.chronologyNotes ? ` | ${snapshot.chronologyNotes}` : ""}
                        </span>
                      </div>
                    </td>
                    <td>
                      <button className="secondary-button" onClick={() => loadSnapshot(snapshot.id)} type="button">
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No snapshots yet.</strong>
            <p className="panel-copy">Use the form below to create the first snapshot immediately after manual project creation.</p>
          </div>
        )}
        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Report ID (optional)</span>
            <input value={snapshotForm.report_id} onChange={(event) => setSnapshotForm((current) => ({ ...current, report_id: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Snapshot date</span>
            <input type="date" value={snapshotForm.snapshot_date} onChange={(event) => setSnapshotForm((current) => ({ ...current, snapshot_date: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Total units</span>
            <input value={snapshotForm.total_units} onChange={(event) => setSnapshotForm((current) => ({ ...current, total_units: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Marketed units</span>
            <input value={snapshotForm.marketed_units} onChange={(event) => setSnapshotForm((current) => ({ ...current, marketed_units: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Sold cumulative</span>
            <input value={snapshotForm.sold_units_cumulative} onChange={(event) => setSnapshotForm((current) => ({ ...current, sold_units_cumulative: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Unsold units</span>
            <input value={snapshotForm.unsold_units} onChange={(event) => setSnapshotForm((current) => ({ ...current, unsold_units: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Avg price per sqm</span>
            <input value={snapshotForm.avg_price_per_sqm_cumulative} onChange={(event) => setSnapshotForm((current) => ({ ...current, avg_price_per_sqm_cumulative: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Gross profit expected</span>
            <input value={snapshotForm.gross_profit_total_expected} onChange={(event) => setSnapshotForm((current) => ({ ...current, gross_profit_total_expected: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Gross margin pct</span>
            <input value={snapshotForm.gross_margin_expected_pct} onChange={(event) => setSnapshotForm((current) => ({ ...current, gross_margin_expected_pct: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Permit status</span>
            <select value={snapshotForm.permit_status} onChange={(event) => setSnapshotForm((current) => ({ ...current, permit_status: event.target.value }))}>
              <option value="">Not disclosed</option>
              {PERMIT_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Project status</span>
            <select value={snapshotForm.project_status} onChange={(event) => setSnapshotForm((current) => ({ ...current, project_status: event.target.value }))}>
              <option value="">Not disclosed</option>
              {PROJECT_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Reviewer note</span>
            <input value={snapshotForm.reviewer_note} onChange={(event) => setSnapshotForm((current) => ({ ...current, reviewer_note: event.target.value }))} />
          </label>
          <label className="filter-field">
            <span>Snapshot note</span>
            <textarea value={snapshotForm.notes_internal} onChange={(event) => setSnapshotForm((current) => ({ ...current, notes_internal: event.target.value }))} />
          </label>
        </div>
        <div className="form-actions">
          <button className="primary-button" disabled={isPending || !snapshotForm.snapshot_date} onClick={handleSaveSnapshot} type="button">
            {snapshotForm.snapshot_id ? "Update snapshot" : "Create snapshot"}
          </button>
          {snapshotForm.snapshot_id ? (
            <button className="secondary-button" disabled={isPending} onClick={() => setSnapshotForm(buildSnapshotForm(item))} type="button">
              New snapshot draft
            </button>
          ) : null}
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Addresses</p>
          <h3>Manage project locations</h3>
        </div>
        {item.addresses.map((address) => {
          const draft = addressDrafts[address.id] ?? buildAddressDraft(address);
          return (
            <div key={address.id} className="address-card section-stack">
              <strong>{formatAddressLabel(address)}</strong>
              <div className="detail-list">
                <div>
                  <strong>Normalized address</strong>
                  <p className="panel-copy">{address.normalizedAddressText ?? "Not normalized yet"}</p>
                </div>
                <div>
                  <strong>Geocoding status</strong>
                  <p className="panel-copy">
                    {[address.geocodingStatus, address.geometrySource, address.locationQuality].join(" | ")}
                  </p>
                </div>
                <div>
                  <strong>Provider</strong>
                  <p className="panel-copy">{address.geocodingProvider ?? "Not set"}</p>
                </div>
                <div>
                  <strong>Note</strong>
                  <p className="panel-copy">{address.geocodingNote ?? "No geocoding note"}</p>
                </div>
                <div>
                  <strong>Method</strong>
                  <p className="panel-copy">{address.geocodingMethod ?? "Not set"}</p>
                </div>
                <div>
                  <strong>Source label</strong>
                  <p className="panel-copy">{address.geocodingSourceLabel ?? "Not set"}</p>
                </div>
              </div>
              <div className="address-inline-form">
                <input placeholder="Raw address text" value={draft.address_text_raw} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, address_text_raw: event.target.value } }))} />
                <input placeholder="Street" value={draft.street} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, street: event.target.value } }))} />
                <input placeholder="House number from" value={draft.house_number_from} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, house_number_from: event.target.value } }))} />
                <input placeholder="House number to" value={draft.house_number_to} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, house_number_to: event.target.value } }))} />
                <input placeholder="City" value={draft.city} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, city: event.target.value } }))} />
                <input placeholder="Latitude" value={draft.lat} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, lat: event.target.value } }))} />
                <input placeholder="Longitude" value={draft.lng} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, lng: event.target.value } }))} />
                <input placeholder="Display address" value={draft.normalized_display_address} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, normalized_display_address: event.target.value } }))} />
                <input placeholder="Geocoding method" value={draft.geocoding_method} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, geocoding_method: event.target.value } }))} />
                <input placeholder="Geocoding source label" value={draft.geocoding_source_label} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, geocoding_source_label: event.target.value } }))} />
                <select value={draft.location_confidence} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, location_confidence: event.target.value } }))}>
                  {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
                <select value={draft.value_origin_type} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, value_origin_type: event.target.value } }))}>
                  {VALUE_ORIGIN_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
                <label className="panel-copy">
                  <input checked={draft.is_primary} type="checkbox" onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, is_primary: event.target.checked } }))} /> Primary
                </label>
                <input placeholder="Change reason" value={draft.change_reason} onChange={(event) => setAddressDrafts((current) => ({ ...current, [address.id]: { ...draft, change_reason: event.target.value } }))} />
                <div className="form-actions">
                  <button className="primary-button" disabled={isPending} onClick={() => saveAddress(address.id)} type="button">
                    Save address
                  </button>
                  <button className="secondary-button" disabled={isPending} onClick={() => normalizeAddress(address.id)} type="button">
                    Normalize
                  </button>
                  <button className="secondary-button" disabled={isPending} onClick={() => geocodeAddress(address.id)} type="button">
                    Geocode
                  </button>
                  <button className="secondary-button" disabled={isPending} onClick={() => removeAddress(address.id)} type="button">
                    Remove
                  </button>
                </div>
              </div>
            </div>
          );
        })}
        <div className="address-card section-stack">
          <strong>Add address</strong>
          <div className="address-inline-form">
            <input placeholder="Raw address text" value={newAddressDraft.address_text_raw} onChange={(event) => setNewAddressDraft((current) => ({ ...current, address_text_raw: event.target.value }))} />
            <input placeholder="Street" value={newAddressDraft.street} onChange={(event) => setNewAddressDraft((current) => ({ ...current, street: event.target.value }))} />
            <input placeholder="House number from" value={newAddressDraft.house_number_from} onChange={(event) => setNewAddressDraft((current) => ({ ...current, house_number_from: event.target.value }))} />
            <input placeholder="House number to" value={newAddressDraft.house_number_to} onChange={(event) => setNewAddressDraft((current) => ({ ...current, house_number_to: event.target.value }))} />
            <input placeholder="City" value={newAddressDraft.city} onChange={(event) => setNewAddressDraft((current) => ({ ...current, city: event.target.value }))} />
            <input placeholder="Latitude" value={newAddressDraft.lat} onChange={(event) => setNewAddressDraft((current) => ({ ...current, lat: event.target.value }))} />
            <input placeholder="Longitude" value={newAddressDraft.lng} onChange={(event) => setNewAddressDraft((current) => ({ ...current, lng: event.target.value }))} />
            <input placeholder="Display address" value={newAddressDraft.normalized_display_address} onChange={(event) => setNewAddressDraft((current) => ({ ...current, normalized_display_address: event.target.value }))} />
            <input placeholder="Geocoding method" value={newAddressDraft.geocoding_method} onChange={(event) => setNewAddressDraft((current) => ({ ...current, geocoding_method: event.target.value }))} />
            <input placeholder="Geocoding source label" value={newAddressDraft.geocoding_source_label} onChange={(event) => setNewAddressDraft((current) => ({ ...current, geocoding_source_label: event.target.value }))} />
            <select value={newAddressDraft.location_confidence} onChange={(event) => setNewAddressDraft((current) => ({ ...current, location_confidence: event.target.value }))}>
              {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            <select value={newAddressDraft.value_origin_type} onChange={(event) => setNewAddressDraft((current) => ({ ...current, value_origin_type: event.target.value }))}>
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            <label className="panel-copy">
              <input checked={newAddressDraft.is_primary} type="checkbox" onChange={(event) => setNewAddressDraft((current) => ({ ...current, is_primary: event.target.checked }))} /> Primary
            </label>
            <input placeholder="Change reason" value={newAddressDraft.change_reason} onChange={(event) => setNewAddressDraft((current) => ({ ...current, change_reason: event.target.value }))} />
            <div className="form-actions">
              <button className="primary-button" disabled={isPending} onClick={() => saveAddress()} type="button">
                Add address
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="admin-grid">
        <div className="admin-form-card section-stack">
          <div>
            <p className="eyebrow">Linked Intake</p>
            <h3>Candidate review history</h3>
          </div>
          {item.linkedCandidates.length > 0 ? (
            item.linkedCandidates.map((candidate) => (
              <div className="candidate-suggestion-card" key={candidate.candidateId}>
                <div>
                  <strong>{candidate.candidateProjectName}</strong>
                  <p className="panel-copy">
                    {[candidate.matchingStatus, candidate.publishStatus, candidate.reviewStatus].join(" | ")}
                  </p>
                </div>
                <Link className="inline-link" href={`/admin/intake/${candidate.candidateId}`}>
                  Open intake
                </Link>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <strong>No linked candidates yet.</strong>
              <p className="panel-copy">Candidates linked from the intake queue will appear here.</p>
            </div>
          )}
        </div>

        <div className="admin-form-card section-stack">
          <div>
            <p className="eyebrow">Linked Sources</p>
            <h3>Supporting reports</h3>
          </div>
          {item.linkedSources.length > 0 ? (
            item.linkedSources.map((source) => (
              <div className="candidate-suggestion-card" key={source.reportId}>
                <div>
                  <strong>{source.reportName ?? "Manual source"}</strong>
                  <p className="panel-copy">
                    {formatDate(source.periodEndDate)} | {source.ingestionStatus}
                  </p>
                </div>
                <Link className="inline-link" href={`/admin/sources/${source.reportId}`}>
                  Open source
                </Link>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <strong>No linked sources yet.</strong>
              <p className="panel-copy">Direct manual edits create hidden manual source records behind the scenes.</p>
            </div>
          )}
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Provenance</p>
          <h3>Value-origin summary</h3>
        </div>
        <div className="tag-row">
          {Object.entries(item.provenanceSummary).map(([key, value]) => (
            <span className="tag" key={key}>
              {key}: {value}
            </span>
          ))}
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
                <th>Origin</th>
                <th>Section</th>
              </tr>
            </thead>
            <tbody>
              {item.fieldProvenance.map((row) => (
                <tr key={`${row.fieldName}-${row.normalizedValue ?? "null"}-${row.sourcePage ?? "na"}`}>
                  <td>{row.fieldName}</td>
                  <td>{row.normalizedValue ?? row.rawValue ?? "Unknown"}</td>
                  <td>{row.valueOriginType}</td>
                  <td>{row.sourceSection ?? "Manual"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Audit</p>
          <h3>Recent admin actions</h3>
        </div>
        {item.auditLog.length > 0 ? (
          <div className="audit-list">
            {item.auditLog.map((entry) => (
              <div className="audit-item" key={entry.id}>
                <div className="audit-item-header">
                  <strong>{entry.action}</strong>
                  <span className="panel-copy">{formatDate(entry.createdAt)}</span>
                </div>
                <p className="panel-copy">{entry.comment ?? "No comment provided."}</p>
                <pre className="panel-copy">{JSON.stringify(entry.diffJson ?? {}, null, 2)}</pre>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>No admin edits have been recorded yet.</strong>
            <p className="panel-copy">The audit trail will populate after the first direct project change.</p>
          </div>
        )}
      </div>
    </div>
  );
}
