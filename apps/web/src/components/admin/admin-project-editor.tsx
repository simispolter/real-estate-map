"use client";

import type { AdminProjectDetail, ProjectAddress, ValueOriginType } from "@real-estat-map/shared";
import {
  GOVERNMENT_PROGRAM_TYPES,
  LOCATION_CONFIDENCE_LEVELS,
  PERMIT_STATUSES,
  PROJECT_BUSINESS_TYPES,
  URBAN_RENEWAL_TYPES,
  VALUE_ORIGIN_TYPES,
} from "@real-estat-map/shared";
import { useState, useTransition } from "react";

import { deleteAdminProjectAddress, updateAdminProject, upsertAdminProjectAddress } from "@/lib/api";
import { formatAddressLabel, formatDate, formatNumber } from "@/lib/format";

type EditableField =
  | "project_business_type"
  | "government_program_type"
  | "project_urban_renewal_type"
  | "permit_status"
  | "city"
  | "neighborhood"
  | "location_confidence";

type ClassificationFormState = {
  project_business_type: string;
  government_program_type: string;
  project_urban_renewal_type: string;
  permit_status: string;
  city: string;
  neighborhood: string;
  location_confidence: string;
  notes_internal: string;
  change_reason: string;
  field_origin_types: Record<EditableField, ValueOriginType | string>;
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
  value_origin_type: string;
  change_reason: string;
};

function buildFormState(project: AdminProjectDetail): ClassificationFormState {
  return {
    project_business_type: project.classification.projectBusinessType,
    government_program_type: project.classification.governmentProgramType,
    project_urban_renewal_type: project.classification.projectUrbanRenewalType,
    permit_status: project.latestSnapshot.permitStatus ?? "",
    city: project.location.city ?? "",
    neighborhood: project.location.neighborhood ?? "",
    location_confidence: project.location.locationConfidence,
    notes_internal: project.notesInternal ?? "",
    change_reason: "",
    field_origin_types: {
      project_business_type: project.classification.trust.project_business_type?.valueOriginType ?? "reported",
      government_program_type: project.classification.trust.government_program_type?.valueOriginType ?? "reported",
      project_urban_renewal_type:
        project.classification.trust.project_urban_renewal_type?.valueOriginType ?? "reported",
      permit_status: project.latestSnapshot.trust.permit_status?.valueOriginType ?? "inferred",
      city: project.location.trust.city?.valueOriginType ?? "reported",
      neighborhood: project.location.trust.neighborhood?.valueOriginType ?? "unknown",
      location_confidence: project.location.trust.location_confidence?.valueOriginType ?? "reported",
    },
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
    location_confidence: "city",
    is_primary: false,
    value_origin_type: "reported",
    change_reason: "",
  };
}

function toAddressDraft(address: ProjectAddress): AddressDraft {
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
    value_origin_type: address.valueOriginType,
    change_reason: "",
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
    value_origin_type: draft.value_origin_type,
    change_reason: draft.change_reason || null,
  };
}

export function AdminProjectEditor({ project }: { project: AdminProjectDetail }) {
  const [item, setItem] = useState(project);
  const [formState, setFormState] = useState<ClassificationFormState>(() => buildFormState(project));
  const [newAddressDraft, setNewAddressDraft] = useState<AddressDraft>(() => emptyAddressDraft(project.location.city));
  const [addressDrafts, setAddressDrafts] = useState<Record<string, AddressDraft>>(() =>
    Object.fromEntries(project.addresses.map((address) => [address.id, toAddressDraft(address)])),
  );
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function syncProject(nextProject: AdminProjectDetail) {
    setItem(nextProject);
    setFormState(buildFormState(nextProject));
    setAddressDrafts(Object.fromEntries(nextProject.addresses.map((address) => [address.id, toAddressDraft(address)])));
    setNewAddressDraft(emptyAddressDraft(nextProject.location.city));
  }

  function handleProjectSave() {
    startTransition(async () => {
      setFeedback(null);
      const result = await updateAdminProject(item.id, {
        project_business_type: formState.project_business_type,
        government_program_type: formState.government_program_type,
        project_urban_renewal_type: formState.project_urban_renewal_type,
        permit_status: formState.permit_status || null,
        city: formState.city || null,
        neighborhood: formState.neighborhood || null,
        location_confidence: formState.location_confidence,
        notes_internal: formState.notes_internal || null,
        field_origin_types: formState.field_origin_types,
        change_reason: formState.change_reason || null,
      });

      if (result.item) {
        syncProject(result.item);
        setFeedback("Project changes saved.");
        return;
      }

      setFeedback("Could not save project changes.");
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
      if (result.item) {
        syncProject(result.item);
        setFeedback(addressId ? "Address updated." : "Address added.");
        return;
      }

      setFeedback("Could not save address changes.");
    });
  }

  function removeAddress(addressId: string) {
    startTransition(async () => {
      setFeedback(null);
      const result = await deleteAdminProjectAddress(item.id, addressId);
      if (result.item) {
        syncProject(result.item);
        setFeedback("Address removed.");
        return;
      }

      setFeedback("Could not remove address.");
    });
  }

  return (
    <div className="section-stack">
      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Admin Review</p>
          <h2>{item.canonicalName}</h2>
          <p className="panel-copy">
            {item.company.nameHe} | latest snapshot {formatDate(item.latestSnapshot.snapshotDate)}
          </p>
        </div>

        {feedback ? <p className="muted-copy">{feedback}</p> : null}

        <div className="admin-form-grid">
          <label className="filter-field">
            <span>Project business type</span>
            <select
              value={formState.project_business_type}
              onChange={(event) => setFormState((current) => ({ ...current, project_business_type: event.target.value }))}
            >
              {PROJECT_BUSINESS_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Origin flag</span>
            <select
              value={formState.field_origin_types.project_business_type}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  field_origin_types: { ...current.field_origin_types, project_business_type: event.target.value },
                }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Government program type</span>
            <select
              value={formState.government_program_type}
              onChange={(event) => setFormState((current) => ({ ...current, government_program_type: event.target.value }))}
            >
              {GOVERNMENT_PROGRAM_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Origin flag</span>
            <select
              value={formState.field_origin_types.government_program_type}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  field_origin_types: { ...current.field_origin_types, government_program_type: event.target.value },
                }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Urban renewal type</span>
            <select
              value={formState.project_urban_renewal_type}
              onChange={(event) =>
                setFormState((current) => ({ ...current, project_urban_renewal_type: event.target.value }))
              }
            >
              {URBAN_RENEWAL_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Origin flag</span>
            <select
              value={formState.field_origin_types.project_urban_renewal_type}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  field_origin_types: { ...current.field_origin_types, project_urban_renewal_type: event.target.value },
                }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Permit status</span>
            <select
              value={formState.permit_status}
              onChange={(event) => setFormState((current) => ({ ...current, permit_status: event.target.value }))}
            >
              <option value="">Not disclosed</option>
              {PERMIT_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Origin flag</span>
            <select
              value={formState.field_origin_types.permit_status}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  field_origin_types: { ...current.field_origin_types, permit_status: event.target.value },
                }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>City</span>
            <input
              value={formState.city}
              onChange={(event) => setFormState((current) => ({ ...current, city: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Origin flag</span>
            <select
              value={formState.field_origin_types.city}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  field_origin_types: { ...current.field_origin_types, city: event.target.value },
                }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Neighborhood</span>
            <input
              value={formState.neighborhood}
              onChange={(event) => setFormState((current) => ({ ...current, neighborhood: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Origin flag</span>
            <select
              value={formState.field_origin_types.neighborhood}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  field_origin_types: { ...current.field_origin_types, neighborhood: event.target.value },
                }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Location confidence</span>
            <select
              value={formState.location_confidence}
              onChange={(event) =>
                setFormState((current) => ({ ...current, location_confidence: event.target.value }))
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
            <span>Origin flag</span>
            <select
              value={formState.field_origin_types.location_confidence}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  field_origin_types: { ...current.field_origin_types, location_confidence: event.target.value },
                }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Internal note</span>
            <textarea
              value={formState.notes_internal}
              onChange={(event) => setFormState((current) => ({ ...current, notes_internal: event.target.value }))}
            />
          </label>
          <label className="filter-field">
            <span>Change reason</span>
            <input
              value={formState.change_reason}
              onChange={(event) => setFormState((current) => ({ ...current, change_reason: event.target.value }))}
            />
          </label>
        </div>

        <div className="form-actions">
          <button className="primary-button" disabled={isPending} onClick={handleProjectSave} type="button">
            Save project review
          </button>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Snapshot</p>
          <h3>Latest project metrics</h3>
          <p className="panel-copy">
            Total units {formatNumber(item.latestSnapshot.totalUnits)} | marketed {formatNumber(item.latestSnapshot.marketedUnits)} | sold {formatNumber(item.latestSnapshot.soldUnitsCumulative)}
          </p>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Addresses</p>
          <h3>Manage project addresses</h3>
        </div>

        {item.addresses.map((address) => {
          const draft = addressDrafts[address.id] ?? toAddressDraft(address);
          return (
            <div key={address.id} className="address-card section-stack">
              <strong>{formatAddressLabel(address)}</strong>
              <div className="address-inline-form">
                <input
                  placeholder="Raw address text"
                  value={draft.address_text_raw}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, address_text_raw: event.target.value },
                    }))
                  }
                />
                <input
                  placeholder="Street"
                  value={draft.street}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, street: event.target.value },
                    }))
                  }
                />
                <input
                  placeholder="House number from"
                  value={draft.house_number_from}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, house_number_from: event.target.value },
                    }))
                  }
                />
                <input
                  placeholder="House number to"
                  value={draft.house_number_to}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, house_number_to: event.target.value },
                    }))
                  }
                />
                <input
                  placeholder="City"
                  value={draft.city}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, city: event.target.value },
                    }))
                  }
                />
                <input
                  placeholder="Latitude"
                  value={draft.lat}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, lat: event.target.value },
                    }))
                  }
                />
                <input
                  placeholder="Longitude"
                  value={draft.lng}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, lng: event.target.value },
                    }))
                  }
                />
                <select
                  value={draft.location_confidence}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, location_confidence: event.target.value },
                    }))
                  }
                >
                  {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
                <select
                  value={draft.value_origin_type}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, value_origin_type: event.target.value },
                    }))
                  }
                >
                  {VALUE_ORIGIN_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
                <label className="panel-copy">
                  <input
                    checked={draft.is_primary}
                    type="checkbox"
                    onChange={(event) =>
                      setAddressDrafts((current) => ({
                        ...current,
                        [address.id]: { ...draft, is_primary: event.target.checked },
                      }))
                    }
                  />{" "}
                  Primary address
                </label>
                <input
                  placeholder="Change reason"
                  value={draft.change_reason}
                  onChange={(event) =>
                    setAddressDrafts((current) => ({
                      ...current,
                      [address.id]: { ...draft, change_reason: event.target.value },
                    }))
                  }
                />
                <div className="form-actions">
                  <button className="primary-button" disabled={isPending} onClick={() => saveAddress(address.id)} type="button">
                    Save address
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
            <input
              placeholder="Raw address text"
              value={newAddressDraft.address_text_raw}
              onChange={(event) => setNewAddressDraft((current) => ({ ...current, address_text_raw: event.target.value }))}
            />
            <input
              placeholder="Street"
              value={newAddressDraft.street}
              onChange={(event) => setNewAddressDraft((current) => ({ ...current, street: event.target.value }))}
            />
            <input
              placeholder="House number from"
              value={newAddressDraft.house_number_from}
              onChange={(event) =>
                setNewAddressDraft((current) => ({ ...current, house_number_from: event.target.value }))
              }
            />
            <input
              placeholder="House number to"
              value={newAddressDraft.house_number_to}
              onChange={(event) =>
                setNewAddressDraft((current) => ({ ...current, house_number_to: event.target.value }))
              }
            />
            <input
              placeholder="City"
              value={newAddressDraft.city}
              onChange={(event) => setNewAddressDraft((current) => ({ ...current, city: event.target.value }))}
            />
            <input
              placeholder="Latitude"
              value={newAddressDraft.lat}
              onChange={(event) => setNewAddressDraft((current) => ({ ...current, lat: event.target.value }))}
            />
            <input
              placeholder="Longitude"
              value={newAddressDraft.lng}
              onChange={(event) => setNewAddressDraft((current) => ({ ...current, lng: event.target.value }))}
            />
            <select
              value={newAddressDraft.location_confidence}
              onChange={(event) =>
                setNewAddressDraft((current) => ({ ...current, location_confidence: event.target.value }))
              }
            >
              {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            <select
              value={newAddressDraft.value_origin_type}
              onChange={(event) =>
                setNewAddressDraft((current) => ({ ...current, value_origin_type: event.target.value }))
              }
            >
              {VALUE_ORIGIN_TYPES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            <label className="panel-copy">
              <input
                checked={newAddressDraft.is_primary}
                type="checkbox"
                onChange={(event) =>
                  setNewAddressDraft((current) => ({ ...current, is_primary: event.target.checked }))
                }
              />{" "}
              Primary address
            </label>
            <input
              placeholder="Change reason"
              value={newAddressDraft.change_reason}
              onChange={(event) => setNewAddressDraft((current) => ({ ...current, change_reason: event.target.value }))}
            />
            <div className="form-actions">
              <button className="primary-button" disabled={isPending} onClick={() => saveAddress()} type="button">
                Add address
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Provenance</p>
          <h3>Field-level source rows</h3>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Normalized</th>
                <th>Origin</th>
                <th>Confidence</th>
                <th>Section</th>
                <th>Reviewer note</th>
              </tr>
            </thead>
            <tbody>
              {item.fieldProvenance.map((row) => (
                <tr key={`${row.fieldName}-${row.sourcePage ?? "na"}-${row.normalizedValue ?? "null"}`}>
                  <td>{row.fieldName}</td>
                  <td>{row.normalizedValue ?? row.rawValue ?? "Unknown"}</td>
                  <td>{row.valueOriginType}</td>
                  <td>{row.confidenceScore ?? "Not scored"}</td>
                  <td>{row.sourceSection ?? "Unknown"}</td>
                  <td>{row.reviewNote ?? "None"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Audit Trail</p>
          <h3>Recent admin changes</h3>
        </div>
        {item.auditLog.length > 0 ? (
          <div className="audit-list">
            {item.auditLog.map((entry) => (
              <div key={entry.id} className="audit-item">
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
            <p className="panel-copy">The audit trail will populate after the first save.</p>
          </div>
        )}
      </div>
    </div>
  );
}
