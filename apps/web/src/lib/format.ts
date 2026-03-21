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

export function formatAddressLabel({
  addressTextRaw,
  street,
  houseNumberFrom,
  houseNumberTo,
  city,
}: {
  addressTextRaw?: string | null;
  street?: string | null;
  houseNumberFrom?: number | null;
  houseNumberTo?: number | null;
  city?: string | null;
}) {
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
