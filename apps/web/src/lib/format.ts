export function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Not disclosed";
  }

  return new Intl.NumberFormat("en-US").format(value);
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Not disclosed";
  }

  return `${value.toFixed(2)}%`;
}

export function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Not disclosed";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "ILS",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not disclosed";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parsed);
}

export function formatEnumLabel(value: string | null | undefined) {
  if (!value) {
    return "Not disclosed";
  }

  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const LIFECYCLE_STAGE_LABELS: Record<string, string> = {
  under_construction: "Under construction",
  completed_unsold_tail: "Completed unsold tail",
  completed_delivered: "Completed delivered",
  planning_advanced: "Advanced planning",
  urban_renewal_pipeline: "Urban renewal pipeline",
  land_reserve: "Land reserve",
};

const DISCLOSURE_LEVEL_LABELS: Record<string, string> = {
  material_very_high: "Material project",
  operational_full: "Operational full disclosure",
  inventory_tail: "Completed inventory tail",
  pipeline_signature: "Pipeline signature disclosure",
  land_reserve: "Land reserve disclosure",
  minimal_reference: "Minimal reference",
};

const SECTION_KIND_LABELS: Record<string, string> = {
  construction: "Construction section",
  planning: "Planning section",
  completed: "Completed inventory section",
  land_reserve: "Land reserve section",
  urban_renewal: "Urban renewal section",
  material_project: "Material project section",
  summary_only: "Summary-only mention",
};

export function formatLifecycleStageLabel(value: string | null | undefined) {
  if (!value) {
    return "Not disclosed";
  }

  return LIFECYCLE_STAGE_LABELS[value] ?? formatEnumLabel(value);
}

export function formatDisclosureLevelLabel(value: string | null | undefined) {
  if (!value) {
    return "Not disclosed";
  }

  return DISCLOSURE_LEVEL_LABELS[value] ?? formatEnumLabel(value);
}

export function formatSectionKindLabel(value: string | null | undefined) {
  if (!value) {
    return "Not disclosed";
  }

  return SECTION_KIND_LABELS[value] ?? formatEnumLabel(value);
}

export function formatLocationQuality(value: string | null | undefined) {
  if (!value) {
    return "Unknown";
  }

  if (value === "city_only" || value === "city-only") {
    return "City-only";
  }

  return formatEnumLabel(value);
}

export function formatOriginBadgeLabel(value: "reported" | "manual" | "inferred") {
  if (value === "manual") {
    return "Manual";
  }
  if (value === "inferred") {
    return "Inferred";
  }
  return "Reported";
}

export function formatAddressLabel({
  addressTextRaw,
  street,
  houseNumberFrom,
  houseNumberTo,
  city,
  parcelBlock,
  parcelNumber,
  subParcel,
}: {
  addressTextRaw?: string | null;
  street?: string | null;
  houseNumberFrom?: number | null;
  houseNumberTo?: number | null;
  city?: string | null;
  parcelBlock?: string | null;
  parcelNumber?: string | null;
  subParcel?: string | null;
}) {
  if (parcelBlock && parcelNumber) {
    const parcelParts = [`גוש ${parcelBlock}`, `חלקה ${parcelNumber}`];
    if (subParcel) {
      parcelParts.push(`תת-חלקה ${subParcel}`);
    }
    if (city) {
      parcelParts.push(city);
    }
    return parcelParts.join(" | ");
  }

  const numberLabel =
    houseNumberFrom && houseNumberTo && houseNumberFrom !== houseNumberTo
      ? `${houseNumberFrom}-${houseNumberTo}`
      : houseNumberFrom
        ? String(houseNumberFrom)
        : houseNumberTo
          ? String(houseNumberTo)
          : null;
  const parts = [street, numberLabel, city].filter(Boolean);

  if (parts.length > 0) {
    return parts.join(" ");
  }

  return addressTextRaw ?? "Not disclosed";
}
