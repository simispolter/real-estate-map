"use client";

import type { AdminLocationReference, AdminProjectDetail, ProjectAddress } from "@real-estat-map/shared";
import { LOCATION_CONFIDENCE_LEVELS } from "@real-estat-map/shared";
import { useEffect, useMemo, useState, useTransition } from "react";

import {
  deleteAdminProjectAddress,
  geocodeAdminProjectAddress,
  getAdminLocationReference,
  updateAdminProject,
  updateAdminProjectDisplayGeometry,
  upsertAdminProjectAddress,
} from "@/lib/api";
import { formatAddressLabel } from "@/lib/format";

import { AdminLocationMapPicker } from "./admin-location-map-picker";

type Props = {
  project: AdminProjectDetail;
  onProjectChange: (nextProject: AdminProjectDetail) => void;
};

type AddressModeDraft = {
  city: string;
  street: string;
  houseNumber: string;
  neighborhood: string;
  note: string;
};

type ParcelModeDraft = {
  city: string;
  block: string;
  parcel: string;
  subParcel: string;
  note: string;
};

type ManualPosition = {
  lat: number | null;
  lng: number | null;
};

const LOCATION_LABELS: Record<string, string> = {
  exact: "מדויק",
  approximate: "בקירוב",
  city_only: "ברמת עיר בלבד",
  unknown: "לא ידוע",
};

function getLocationLabel(value: string | null | undefined) {
  return LOCATION_LABELS[value ?? "unknown"] ?? "לא ידוע";
}

function getPrimaryAddress(addresses: ProjectAddress[]) {
  return addresses.find((address) => address.isPrimary) ?? addresses[0] ?? null;
}

function formatProjectAddress(address: ProjectAddress | null) {
  if (!address) {
    return "עדיין לא הוגדרה כתובת";
  }
  return formatAddressLabel(address);
}

function buildAddressDraft(project: AdminProjectDetail, address: ProjectAddress | null): AddressModeDraft {
  return {
    city: address?.city ?? project.location.city ?? "",
    street: address?.street ?? "",
    houseNumber: address?.houseNumberFrom?.toString() ?? "",
    neighborhood: project.location.neighborhood ?? "",
    note: address?.addressNote ?? "",
  };
}

function buildParcelDraft(project: AdminProjectDetail, address: ProjectAddress | null): ParcelModeDraft {
  return {
    city: address?.city ?? project.location.city ?? "",
    block: address?.parcelBlock ?? "",
    parcel: address?.parcelNumber ?? "",
    subParcel: address?.subParcel ?? "",
    note: address?.addressNote ?? "",
  };
}

function detectMode(address: ProjectAddress | null): "address" | "parcel" {
  if (address?.parcelBlock && address?.parcelNumber && !address.street) {
    return "parcel";
  }
  return "address";
}

function buildManualPosition(project: AdminProjectDetail, address: ProjectAddress | null): ManualPosition {
  return {
    lat: address?.lat ?? project.displayGeometry.centerLat ?? null,
    lng: address?.lng ?? project.displayGeometry.centerLng ?? null,
  };
}

function buildAddressPayload(
  draft: AddressModeDraft,
  quality: string,
  position: ManualPosition,
  changeReason: string,
) {
  const rawAddress = [draft.street, draft.houseNumber, draft.city].filter(Boolean).join(" ").trim();
  return {
    address_text_raw: rawAddress || null,
    street: draft.street || null,
    house_number_from: draft.houseNumber ? Number(draft.houseNumber) : null,
    house_number_to: draft.houseNumber ? Number(draft.houseNumber) : null,
    city: draft.city || null,
    address_note: draft.note || null,
    lat: position.lat,
    lng: position.lng,
    location_confidence: quality,
    is_primary: true,
    geocoding_method: position.lat !== null && position.lng !== null ? "manual_point" : null,
    geocoding_source_label: position.lat !== null && position.lng !== null ? "מיקום ידני באדמין" : null,
    value_origin_type: "manual",
    change_reason: changeReason || null,
  };
}

function buildParcelPayload(
  draft: ParcelModeDraft,
  quality: string,
  position: ManualPosition,
  changeReason: string,
) {
  const rawAddress = [`גוש ${draft.block}`, `חלקה ${draft.parcel}`];
  if (draft.subParcel) {
    rawAddress.push(`תת-חלקה ${draft.subParcel}`);
  }

  return {
    address_text_raw: rawAddress.join(" "),
    city: draft.city || null,
    parcel_block: draft.block || null,
    parcel_number: draft.parcel || null,
    sub_parcel: draft.subParcel || null,
    address_note: draft.note || null,
    lat: position.lat,
    lng: position.lng,
    location_confidence: quality,
    is_primary: true,
    geocoding_method: position.lat !== null && position.lng !== null ? "parcel_manual" : null,
    geocoding_source_label: position.lat !== null && position.lng !== null ? "איתור ידני לפי גוש / חלקה" : null,
    value_origin_type: "manual",
    change_reason: changeReason || null,
  };
}

export function AdminProjectLocationManager({ onProjectChange, project }: Props) {
  const primaryAddress = useMemo(() => getPrimaryAddress(project.addresses), [project.addresses]);
  const [mode, setMode] = useState<"address" | "parcel">(() => detectMode(primaryAddress));
  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(primaryAddress?.id ?? null);
  const [addressDraft, setAddressDraft] = useState<AddressModeDraft>(() => buildAddressDraft(project, primaryAddress));
  const [parcelDraft, setParcelDraft] = useState<ParcelModeDraft>(() => buildParcelDraft(project, primaryAddress));
  const [manualPosition, setManualPosition] = useState<ManualPosition>(() => buildManualPosition(project, primaryAddress));
  const [locationConfidence, setLocationConfidence] = useState<string>(
    primaryAddress?.locationConfidence ?? project.location.locationConfidence ?? "unknown",
  );
  const [changeReason, setChangeReason] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [referenceOptions, setReferenceOptions] = useState<AdminLocationReference>({ cities: [], streets: [] });
  const [citiesState, setCitiesState] = useState<AdminLocationReference>({ cities: [], streets: [] });
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const nextPrimary = getPrimaryAddress(project.addresses);
    setSelectedAddressId(nextPrimary?.id ?? null);
    setMode(detectMode(nextPrimary));
    setAddressDraft(buildAddressDraft(project, nextPrimary));
    setParcelDraft(buildParcelDraft(project, nextPrimary));
    setManualPosition(buildManualPosition(project, nextPrimary));
    setLocationConfidence(nextPrimary?.locationConfidence ?? project.location.locationConfidence ?? "unknown");
  }, [project]);

  useEffect(() => {
    let cancelled = false;
    void getAdminLocationReference().then((result) => {
      if (cancelled || !result.item) {
        return;
      }
      setCitiesState(result.item);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeCity = mode === "address" ? addressDraft.city : parcelDraft.city;

  useEffect(() => {
    let cancelled = false;
    void getAdminLocationReference(activeCity ? { city: activeCity } : {}).then((result) => {
      if (cancelled || !result.item) {
        return;
      }
      setReferenceOptions(result.item);
    });
    return () => {
      cancelled = true;
    };
  }, [activeCity]);

  const currentAddress =
    project.addresses.find((address) => address.id === selectedAddressId) ??
    primaryAddress;

  async function syncProjectLocation(nextProject: AdminProjectDetail, nextCity: string, nextNeighborhood: string, nextConfidence: string) {
    const updateResult = await updateAdminProject(project.id, {
      city: nextCity || null,
      neighborhood: nextNeighborhood || null,
      location_confidence: nextConfidence,
      field_origin_types: {
        city: "manual",
        neighborhood: "manual",
        location_confidence: "manual",
      },
      change_reason: changeReason || null,
    });
    if (updateResult.item) {
      onProjectChange(updateResult.item);
      return updateResult.item;
    }
    onProjectChange(nextProject);
    return nextProject;
  }

  function loadAddress(address: ProjectAddress, sourceProject: AdminProjectDetail = project) {
    setSelectedAddressId(address.id);
    setMode(detectMode(address));
    setAddressDraft(buildAddressDraft(sourceProject, address));
    setParcelDraft(buildParcelDraft(sourceProject, address));
    setManualPosition(buildManualPosition(sourceProject, address));
    setLocationConfidence(address.locationConfidence);
    setFeedback(null);
  }

  function startNewEntry(nextMode: "address" | "parcel" = mode) {
    setSelectedAddressId(null);
    setMode(nextMode);
    setAddressDraft(buildAddressDraft(project, null));
    setParcelDraft(buildParcelDraft(project, null));
    setManualPosition({
      lat: project.displayGeometry.centerLat ?? null,
      lng: project.displayGeometry.centerLng ?? null,
    });
    setLocationConfidence(project.location.locationConfidence ?? "city_only");
    setFeedback(null);
  }

  function handleLocateByAddress() {
    if (!addressDraft.city || !addressDraft.street) {
      setFeedback("יש לבחור עיר ורחוב לפני איתור על המפה.");
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const upsertResult = await upsertAdminProjectAddress(
        project.id,
        buildAddressPayload(addressDraft, locationConfidence, { lat: null, lng: null }, changeReason),
        selectedAddressId ?? undefined,
      );
      if (!upsertResult.item) {
        setFeedback("לא הצלחנו לשמור את הכתובת.");
        return;
      }

      const savedPrimary = getPrimaryAddress(upsertResult.item.addresses);
      if (!savedPrimary) {
        onProjectChange(upsertResult.item);
        setFeedback("הכתובת נשמרה, אבל לא נמצאה כתובת פעילה לאיתור.");
        return;
      }

      const geocodeResult = await geocodeAdminProjectAddress(project.id, savedPrimary.id);
      if (!geocodeResult.item) {
        onProjectChange(upsertResult.item);
        setFeedback("הכתובת נשמרה, אבל לא הצלחנו לאתר אותה על המפה.");
        return;
      }

      const geocodedAddress = getPrimaryAddress(geocodeResult.item.addresses);
      const nextConfidence = geocodedAddress?.locationConfidence ?? locationConfidence;
      const nextProject = await syncProjectLocation(
        geocodeResult.item,
        addressDraft.city,
        addressDraft.neighborhood,
        nextConfidence,
      );
      const nextPrimary = getPrimaryAddress(nextProject.addresses);
      if (nextPrimary) {
        loadAddress(nextPrimary, nextProject);
      }
      setFeedback("הכתובת אותרה והוצבה על המפה.");
    });
  }

  function handleLocateByParcel() {
    if (!parcelDraft.city || !parcelDraft.block || !parcelDraft.parcel) {
      setFeedback("יש למלא עיר, גוש וחלקה לפני שמירה.");
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const nextPosition =
        manualPosition.lat !== null && manualPosition.lng !== null
          ? manualPosition
          : {
              lat: project.displayGeometry.centerLat ?? null,
              lng: project.displayGeometry.centerLng ?? null,
            };
      const upsertResult = await upsertAdminProjectAddress(
        project.id,
        buildParcelPayload(parcelDraft, locationConfidence, nextPosition, changeReason),
        selectedAddressId ?? undefined,
      );
      if (!upsertResult.item) {
        setFeedback("לא הצלחנו לשמור את פרטי הגוש / חלקה.");
        return;
      }

      const nextConfidence = nextPosition.lat !== null && nextPosition.lng !== null ? locationConfidence : "city_only";
      const nextProject = await syncProjectLocation(upsertResult.item, parcelDraft.city, project.location.neighborhood ?? "", nextConfidence);
      const nextPrimary = getPrimaryAddress(nextProject.addresses);
      if (nextPrimary) {
        loadAddress(nextPrimary, nextProject);
      }
      setFeedback(
        nextPosition.lat !== null && nextPosition.lng !== null
          ? "המיקום לפי גוש / חלקה נשמר עם הצבה על המפה."
          : "פרטי הגוש / חלקה נשמרו. אפשר לכוונן את הסמן על המפה ולשמור מיקום בקירוב.",
      );
    });
  }

  function handleSaveManualPlacement() {
    if (manualPosition.lat === null || manualPosition.lng === null) {
      setFeedback("יש לבחור נקודה על המפה לפני השמירה.");
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      if (mode === "address") {
        const upsertResult = await upsertAdminProjectAddress(
          project.id,
          buildAddressPayload(addressDraft, locationConfidence, manualPosition, changeReason),
          selectedAddressId ?? undefined,
        );
        if (!upsertResult.item) {
          setFeedback("לא הצלחנו לשמור את המיקום הידני.");
          return;
        }
        const nextProject = await syncProjectLocation(
          upsertResult.item,
          addressDraft.city,
          addressDraft.neighborhood,
          locationConfidence,
        );
        const nextPrimary = getPrimaryAddress(nextProject.addresses);
        if (nextPrimary) {
          loadAddress(nextPrimary, nextProject);
        }
        setFeedback("המיקום הידני נשמר בהצלחה.");
        return;
      }

      const upsertResult = await upsertAdminProjectAddress(
        project.id,
        buildParcelPayload(parcelDraft, locationConfidence, manualPosition, changeReason),
        selectedAddressId ?? undefined,
      );
      if (!upsertResult.item) {
        setFeedback("לא הצלחנו לשמור את ההצבה הידנית.");
        return;
      }
      const nextProject = await syncProjectLocation(
        upsertResult.item,
        parcelDraft.city,
        project.location.neighborhood ?? "",
        locationConfidence,
      );
      const nextPrimary = getPrimaryAddress(nextProject.addresses);
      if (nextPrimary) {
        loadAddress(nextPrimary, nextProject);
      }
      setFeedback("ההצבה הידנית לפי גוש / חלקה נשמרה.");
    });
  }

  function handleRemoveAddress(addressId: string) {
    startTransition(async () => {
      setFeedback(null);
      const result = await deleteAdminProjectAddress(project.id, addressId);
      if (!result.item) {
        setFeedback("לא הצלחנו להסיר את הכתובת.");
        return;
      }
      onProjectChange(result.item);
      setFeedback("הכתובת הוסרה.");
    });
  }

  function handleAdvancedProjectSave() {
    startTransition(async () => {
      setFeedback(null);
      const result = await updateAdminProjectDisplayGeometry(project.id, {
        geometry_type:
          manualPosition.lat !== null && manualPosition.lng !== null
            ? locationConfidence === "exact"
              ? "exact_point"
              : "approximate_point"
            : locationConfidence === "city_only"
              ? "city_centroid"
              : "unknown",
        geometry_source: "manual_override",
        location_confidence: locationConfidence,
        center_lat: manualPosition.lat,
        center_lng: manualPosition.lng,
        address_summary:
          mode === "address"
            ? [addressDraft.street, addressDraft.houseNumber, addressDraft.city].filter(Boolean).join(" ").trim() || addressDraft.city || null
            : [`גוש ${parcelDraft.block}`, `חלקה ${parcelDraft.parcel}`, parcelDraft.city].filter(Boolean).join(" | "),
        note: mode === "address" ? addressDraft.note || null : parcelDraft.note || null,
        change_reason: changeReason || null,
      });
      if (!result.item) {
        setFeedback("לא הצלחנו לשמור את ההגדרה המתקדמת.");
        return;
      }
      onProjectChange(result.item);
      setFeedback("הגדרת המיקום המתקדמת נשמרה.");
    });
  }

  const assignmentMethodLabel =
    currentAddress?.parcelBlock && currentAddress?.parcelNumber
      ? "גוש / חלקה"
      : currentAddress?.street || currentAddress?.addressTextRaw
        ? "כתובת"
        : project.displayGeometry.isManualOverride
          ? "ידני"
          : "ברמת עיר";

  return (
    <div className="admin-form-card section-stack location-manager-card" dir="rtl">
      <div className="location-summary-header">
        <div>
          <p className="eyebrow">ניהול מיקום</p>
          <h3>שיוך מיקום לפרויקט</h3>
          <p className="panel-copy">בחרו אם לעבוד לפי כתובת או לפי גוש / חלקה. כל הפעולות נשמרות עם audit מאחורי הקלעים.</p>
        </div>
        {feedback ? <p className="muted-copy">{feedback}</p> : null}
      </div>

      <div className="location-status-grid">
        <div className="location-status-card">
          <strong>סטטוס מיקום</strong>
          <span>{project.displayGeometry.hasCoordinates ? "יש מיקום על המפה" : "חסר מיקום מדויק"}</span>
        </div>
        <div className="location-status-card">
          <strong>שיטת שיוך</strong>
          <span>{assignmentMethodLabel}</span>
        </div>
        <div className="location-status-card">
          <strong>כתובת נוכחית</strong>
          <span>{formatProjectAddress(currentAddress)}</span>
        </div>
        <div className="location-status-card">
          <strong>איכות מיקום</strong>
          <span>{getLocationLabel(project.location.locationConfidence)}</span>
        </div>
      </div>

      <div className="location-mode-tabs">
        <button
          className={`secondary-button ${mode === "address" ? "location-tab-active" : ""}`}
          onClick={() => setMode("address")}
          type="button"
        >
          כתובת
        </button>
        <button
          className={`secondary-button ${mode === "parcel" ? "location-tab-active" : ""}`}
          onClick={() => setMode("parcel")}
          type="button"
        >
          גוש / חלקה
        </button>
      </div>

      {project.addresses.length > 0 ? (
        <div className="section-stack">
          <div className="form-actions">
            <button className="secondary-button" onClick={() => startNewEntry("address")} type="button">
              כתובת חדשה
            </button>
            <button className="secondary-button" onClick={() => startNewEntry("parcel")} type="button">
              שיוך חדש לפי גוש / חלקה
            </button>
          </div>
          <div className="location-address-list">
            {project.addresses.map((address) => (
              <div className={`location-address-chip ${selectedAddressId === address.id ? "location-address-chip-active" : ""}`} key={address.id}>
                <div className="stacked-cell">
                  <strong>{formatAddressLabel(address)}</strong>
                  <span className="muted-copy">
                    {getLocationLabel(address.locationConfidence)} | {address.isPrimary ? "כתובת ראשית" : "כתובת משנית"}
                  </span>
                </div>
                <div className="form-actions">
                  <button className="secondary-button" onClick={() => loadAddress(address)} type="button">
                    עריכה
                  </button>
                  <button className="secondary-button" disabled={isPending} onClick={() => handleRemoveAddress(address.id)} type="button">
                    הסרה
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <strong>עדיין אין לפרויקט כתובת שמישה.</strong>
          <p className="panel-copy">התחילו בהזנת כתובת או גוש / חלקה, ואז שמרו והציבו את המיקום על המפה.</p>
        </div>
      )}

      {mode === "address" ? (
        <div className="location-workflow-grid">
          <div className="section-stack">
            <div className="admin-form-grid">
              <label className="filter-field">
                <span>עיר</span>
                <input
                  list="admin-location-cities"
                  onChange={(event) => setAddressDraft((current) => ({ ...current, city: event.target.value }))}
                  placeholder="התחילו להקליד עיר"
                  value={addressDraft.city}
                />
              </label>
              <label className="filter-field">
                <span>רחוב</span>
                <input
                  list="admin-location-streets"
                  onChange={(event) => setAddressDraft((current) => ({ ...current, street: event.target.value }))}
                  placeholder={addressDraft.city ? "התחילו להקליד רחוב" : "בחרו קודם עיר"}
                  value={addressDraft.street}
                />
              </label>
              <label className="filter-field">
                <span>מספר בית</span>
                <input
                  inputMode="numeric"
                  onChange={(event) => setAddressDraft((current) => ({ ...current, houseNumber: event.target.value }))}
                  placeholder="למשל 14"
                  value={addressDraft.houseNumber}
                />
              </label>
              <label className="filter-field">
                <span>שכונה (אופציונלי)</span>
                <input
                  onChange={(event) => setAddressDraft((current) => ({ ...current, neighborhood: event.target.value }))}
                  placeholder="אם ידוע"
                  value={addressDraft.neighborhood}
                />
              </label>
              <label className="filter-field location-wide-field">
                <span>הערת כתובת (אופציונלי)</span>
                <textarea
                  onChange={(event) => setAddressDraft((current) => ({ ...current, note: event.target.value }))}
                  placeholder="למשל כניסה אחורית, שם מתחם או פרטי זיהוי נוספים"
                  value={addressDraft.note}
                />
              </label>
            </div>
            <div className="form-actions">
              <button className="primary-button" disabled={isPending} onClick={handleLocateByAddress} type="button">
                בדיקה והצבה על המפה
              </button>
              <span className="muted-copy">אם נמצאה כתובת, המערכת תנסה להציב אותה על המפה בדיוק המרבי האפשרי.</span>
            </div>
          </div>
          <div className="section-stack">
            <div className="location-confidence-row">
              {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                <button
                  className={`secondary-button ${locationConfidence === value ? "location-tab-active" : ""}`}
                  key={value}
                  onClick={() => setLocationConfidence(value)}
                  type="button"
                >
                  {getLocationLabel(value)}
                </button>
              ))}
            </div>
            <AdminLocationMapPicker
              fallbackLat={project.displayGeometry.centerLat}
              fallbackLng={project.displayGeometry.centerLng}
              lat={manualPosition.lat}
              lng={manualPosition.lng}
              onChange={setManualPosition}
              qualityLabel={getLocationLabel(locationConfidence)}
            />
            <div className="form-actions">
              <button className="primary-button" disabled={isPending} onClick={handleSaveManualPlacement} type="button">
                שמירת המיקום על המפה
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="location-workflow-grid">
          <div className="section-stack">
            <div className="admin-form-grid">
              <label className="filter-field">
                <span>עיר</span>
                <input
                  list="admin-location-cities"
                  onChange={(event) => setParcelDraft((current) => ({ ...current, city: event.target.value }))}
                  placeholder="התחילו להקליד עיר"
                  value={parcelDraft.city}
                />
              </label>
              <label className="filter-field">
                <span>גוש</span>
                <input
                  onChange={(event) => setParcelDraft((current) => ({ ...current, block: event.target.value }))}
                  placeholder="למשל 7102"
                  value={parcelDraft.block}
                />
              </label>
              <label className="filter-field">
                <span>חלקה</span>
                <input
                  onChange={(event) => setParcelDraft((current) => ({ ...current, parcel: event.target.value }))}
                  placeholder="למשל 48"
                  value={parcelDraft.parcel}
                />
              </label>
              <label className="filter-field">
                <span>תת-חלקה / פירוט נוסף (אופציונלי)</span>
                <input
                  onChange={(event) => setParcelDraft((current) => ({ ...current, subParcel: event.target.value }))}
                  placeholder="אם ידוע"
                  value={parcelDraft.subParcel}
                />
              </label>
              <label className="filter-field location-wide-field">
                <span>הערה (אופציונלי)</span>
                <textarea
                  onChange={(event) => setParcelDraft((current) => ({ ...current, note: event.target.value }))}
                  placeholder="למשל מקור הנתון או הסבר למיקום בקירוב"
                  value={parcelDraft.note}
                />
              </label>
            </div>
            <div className="form-actions">
              <button className="primary-button" disabled={isPending} onClick={handleLocateByParcel} type="button">
                איתור לפי גוש / חלקה
              </button>
              <span className="muted-copy">אם אין גיאומטריה מדויקת לחלקה, אפשר להציב מיקום בקירוב על המפה ולשמור אותו ידנית.</span>
            </div>
          </div>
          <div className="section-stack">
            <div className="location-confidence-row">
              {LOCATION_CONFIDENCE_LEVELS.map((value) => (
                <button
                  className={`secondary-button ${locationConfidence === value ? "location-tab-active" : ""}`}
                  key={value}
                  onClick={() => setLocationConfidence(value)}
                  type="button"
                >
                  {getLocationLabel(value)}
                </button>
              ))}
            </div>
            <AdminLocationMapPicker
              fallbackLat={project.displayGeometry.centerLat}
              fallbackLng={project.displayGeometry.centerLng}
              lat={manualPosition.lat}
              lng={manualPosition.lng}
              onChange={setManualPosition}
              qualityLabel={getLocationLabel(locationConfidence)}
            />
            <div className="form-actions">
              <button className="primary-button" disabled={isPending} onClick={handleSaveManualPlacement} type="button">
                שמירת מיקום בקירוב
              </button>
            </div>
          </div>
        </div>
      )}

      <datalist id="admin-location-cities">
        {citiesState.cities.map((city) => (
          <option key={city} value={city} />
        ))}
      </datalist>
      <datalist id="admin-location-streets">
        {referenceOptions.streets.map((street) => (
          <option key={street} value={street} />
        ))}
      </datalist>

      <details className="admin-location-advanced">
        <summary>פרטים מתקדמים</summary>
        <div className="admin-form-grid">
          <label className="filter-field">
            <span>סיבת שינוי</span>
            <input
              onChange={(event) => setChangeReason(event.target.value)}
              placeholder="אופציונלי, לשמירה ב-audit"
              value={changeReason}
            />
          </label>
          <label className="filter-field">
            <span>קו רוחב</span>
            <input
              onChange={(event) =>
                setManualPosition((current) => ({
                  ...current,
                  lat: event.target.value ? Number(event.target.value) : null,
                }))
              }
              value={manualPosition.lat ?? ""}
            />
          </label>
          <label className="filter-field">
            <span>קו אורך</span>
            <input
              onChange={(event) =>
                setManualPosition((current) => ({
                  ...current,
                  lng: event.target.value ? Number(event.target.value) : null,
                }))
              }
              value={manualPosition.lng ?? ""}
            />
          </label>
          <div className="detail-list location-advanced-meta">
            <div>
              <strong>סטטוס geocoding</strong>
              <p className="panel-copy">{currentAddress?.geocodingStatus ?? "לא קיים"}</p>
            </div>
            <div>
              <strong>שיטת geocoding</strong>
              <p className="panel-copy">{currentAddress?.geocodingMethod ?? "לא קיים"}</p>
            </div>
            <div>
              <strong>מקור מיקום</strong>
              <p className="panel-copy">{project.displayGeometry.geometrySource}</p>
            </div>
            <div>
              <strong>מקור שיוך</strong>
              <p className="panel-copy">{currentAddress?.geocodingSourceLabel ?? "ידני / לא הוגדר"}</p>
            </div>
          </div>
        </div>
        <div className="form-actions">
          <button className="secondary-button" disabled={isPending} onClick={handleAdvancedProjectSave} type="button">
            שמירה מתקדמת ברמת הפרויקט
          </button>
        </div>
      </details>
    </div>
  );
}
