import type {
  AdminAddressCandidate,
  AdminCandidateDetail,
  AdminCandidateSummary,
  AdminFieldCandidate,
  AdminProjectDetail,
  AdminProjectListItem,
  AdminReportDetail,
  AdminReportSummary,
  CandidateCompareRow,
  CandidateDiffItem,
  CompanyDetail,
  CompanyListItem,
  FieldProvenance,
  FiltersMetadata,
  KpiDefinition,
  MatchSuggestion,
  MapProjectsResponse,
  ProjectAddress,
  ProjectDetail,
  ProjectHistoryItem,
  ProjectListItem,
  ValueTrust,
} from "@real-estat-map/shared";

type DataState = "ready" | "empty" | "error";

type ApiOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: Record<string, unknown> | null;
  searchParams?: URLSearchParams;
};

function getApiBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_BASE_URL ?? "http://api:8000";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T | null> {
  const query = options.searchParams && options.searchParams.toString() ? `?${options.searchParams.toString()}` : "";
  const apiBaseUrl = getApiBaseUrl();

  try {
    const response = await fetch(`${apiBaseUrl}${path}${query}`, {
      method: options.method ?? "GET",
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    if (response.status === 204) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

function safeArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function safeObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function stringOrNull(value: unknown) {
  return typeof value === "string" ? value : null;
}

function numberOrNull(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function mapTrustMap(value: unknown): Record<string, ValueTrust> {
  const trustMap = safeObject(value);

  return Object.fromEntries(
    Object.entries(trustMap).map(([fieldName, trustValue]) => {
      const trustObject = safeObject(trustValue);
      return [
        fieldName,
        {
          valueOriginType: stringOrNull(trustObject.value_origin_type) ?? "unknown",
          confidenceLevel: stringOrNull(trustObject.confidence_level) ?? "low",
        },
      ];
    }),
  );
}

function mapProjectListItem(item: Record<string, unknown>, index: number): ProjectListItem {
  const company = safeObject(item.company);
  return {
    projectId: stringOrNull(item.project_id) ?? `missing-project-${index}`,
    canonicalName: stringOrNull(item.canonical_name) ?? "Unnamed project",
    company: {
      id: stringOrNull(company.id) ?? "unknown-company",
      nameHe: stringOrNull(company.name_he) ?? "Unknown company",
    },
    city: stringOrNull(item.city),
    neighborhood: stringOrNull(item.neighborhood),
    projectBusinessType: stringOrNull(item.project_business_type) ?? "unknown",
    governmentProgramType: stringOrNull(item.government_program_type) ?? "none",
    projectUrbanRenewalType: stringOrNull(item.project_urban_renewal_type) ?? "none",
    projectStatus: stringOrNull(item.project_status),
    permitStatus: stringOrNull(item.permit_status),
    totalUnits: numberOrNull(item.total_units),
    marketedUnits: numberOrNull(item.marketed_units),
    soldUnitsCumulative: numberOrNull(item.sold_units_cumulative),
    unsoldUnits: numberOrNull(item.unsold_units),
    avgPricePerSqmCumulative: numberOrNull(item.avg_price_per_sqm_cumulative),
    grossProfitTotalExpected: numberOrNull(item.gross_profit_total_expected),
    grossMarginExpectedPct: numberOrNull(item.gross_margin_expected_pct),
    latestSnapshotDate: stringOrNull(item.latest_snapshot_date),
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    locationQuality: stringOrNull(item.location_quality) ?? "unknown",
    sellThroughRate: numberOrNull(item.sell_through_rate),
  };
}

function mapFieldProvenance(item: Record<string, unknown>, index: number): FieldProvenance {
  return {
    fieldName: stringOrNull(item.field_name) ?? `field-${index}`,
    rawValue: stringOrNull(item.raw_value),
    normalizedValue: stringOrNull(item.normalized_value),
    sourcePage: numberOrNull(item.source_page),
    sourceSection: stringOrNull(item.source_section),
    extractionMethod: stringOrNull(item.extraction_method) ?? "unknown",
    confidenceScore: numberOrNull(item.confidence_score),
    valueOriginType: stringOrNull(item.value_origin_type) ?? "unknown",
    reviewStatus: stringOrNull(item.review_status) ?? "pending",
    reviewNote: stringOrNull(item.review_note),
  };
}

function mapAddress(item: Record<string, unknown>, index: number): ProjectAddress {
  return {
    id: stringOrNull(item.id) ?? `address-${index}`,
    addressTextRaw: stringOrNull(item.address_text_raw),
    city: stringOrNull(item.city),
    street: stringOrNull(item.street),
    houseNumberFrom: numberOrNull(item.house_number_from),
    houseNumberTo: numberOrNull(item.house_number_to),
    lat: numberOrNull(item.lat),
    lng: numberOrNull(item.lng),
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    locationQuality: stringOrNull(item.location_quality) ?? "unknown",
    isPrimary: Boolean(item.is_primary),
    valueOriginType: stringOrNull(item.value_origin_type) ?? "unknown",
  };
}

function mapAdminFieldCandidate(item: Record<string, unknown>, index: number): AdminFieldCandidate {
  return {
    id: stringOrNull(item.id) ?? `field-candidate-${index}`,
    fieldName: stringOrNull(item.field_name) ?? "unknown_field",
    rawValue: stringOrNull(item.raw_value),
    normalizedValue: stringOrNull(item.normalized_value),
    sourcePage: numberOrNull(item.source_page),
    sourceSection: stringOrNull(item.source_section),
    valueOriginType: stringOrNull(item.value_origin_type) ?? "unknown",
    confidenceLevel: stringOrNull(item.confidence_level) ?? "low",
    reviewStatus: stringOrNull(item.review_status) ?? "pending",
    reviewNotes: stringOrNull(item.review_notes),
    createdAt: stringOrNull(item.created_at) ?? "",
    updatedAt: stringOrNull(item.updated_at) ?? "",
  };
}

function mapAdminAddressCandidate(item: Record<string, unknown>, index: number): AdminAddressCandidate {
  return {
    id: stringOrNull(item.id) ?? `address-candidate-${index}`,
    addressTextRaw: stringOrNull(item.address_text_raw),
    street: stringOrNull(item.street),
    houseNumberFrom: numberOrNull(item.house_number_from),
    houseNumberTo: numberOrNull(item.house_number_to),
    city: stringOrNull(item.city),
    lat: numberOrNull(item.lat),
    lng: numberOrNull(item.lng),
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    isPrimary: Boolean(item.is_primary),
    valueOriginType: stringOrNull(item.value_origin_type) ?? "unknown",
    confidenceLevel: stringOrNull(item.confidence_level) ?? "low",
    reviewStatus: stringOrNull(item.review_status) ?? "pending",
    reviewNotes: stringOrNull(item.review_notes),
    createdAt: stringOrNull(item.created_at) ?? "",
    updatedAt: stringOrNull(item.updated_at) ?? "",
  };
}

function mapAdminCandidateSummary(item: Record<string, unknown>, index: number): AdminCandidateSummary {
  return {
    id: stringOrNull(item.id) ?? `candidate-${index}`,
    candidateProjectName: stringOrNull(item.candidate_project_name) ?? "Unnamed candidate",
    city: stringOrNull(item.city),
    neighborhood: stringOrNull(item.neighborhood),
    matchingStatus: stringOrNull(item.matching_status) ?? "unmatched",
    publishStatus: stringOrNull(item.publish_status) ?? "draft",
    confidenceLevel: stringOrNull(item.confidence_level) ?? "low",
    reviewStatus: stringOrNull(item.review_status) ?? "pending",
    matchedProjectId: stringOrNull(item.matched_project_id),
    matchedProjectName: stringOrNull(item.matched_project_name),
    reviewNotes: stringOrNull(item.review_notes),
    diffSummary: item.diff_summary && typeof item.diff_summary === "object" ? (item.diff_summary as Record<string, unknown>) : null,
  };
}

function mapMatchSuggestion(item: Record<string, unknown>, index: number): MatchSuggestion {
  return {
    projectId: stringOrNull(item.project_id) ?? `suggestion-${index}`,
    canonicalName: stringOrNull(item.canonical_name) ?? "Unnamed project",
    city: stringOrNull(item.city),
    neighborhood: stringOrNull(item.neighborhood),
    similarityScore: numberOrNull(item.similarity_score) ?? 0,
  };
}

function mapCandidateCompareRow(item: Record<string, unknown>, index: number): CandidateCompareRow {
  return {
    fieldName: stringOrNull(item.field_name) ?? `compare-${index}`,
    canonicalValue: stringOrNull(item.canonical_value),
    stagingValue: stringOrNull(item.staging_value),
    rawSourceValue: stringOrNull(item.raw_source_value),
    sourcePage: numberOrNull(item.source_page),
    sourceSection: stringOrNull(item.source_section),
    valueOriginType: stringOrNull(item.value_origin_type) ?? "unknown",
    confidenceLevel: stringOrNull(item.confidence_level) ?? "low",
    changed: Boolean(item.changed),
  };
}

function mapCandidateDiffItem(item: Record<string, unknown>, index: number): CandidateDiffItem {
  return {
    fieldName: stringOrNull(item.field_name) ?? `diff-${index}`,
    previousValue: stringOrNull(item.previous_value),
    incomingValue: stringOrNull(item.incoming_value),
    changed: Boolean(item.changed),
  };
}

function buildSearchParams(filters: Record<string, string | undefined>) {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      searchParams.set(key, value);
    }
  }
  return searchParams;
}

function mapProjectDetail(response: Record<string, unknown>, fallbackId: string): ProjectDetail {
  const identity = safeObject(response.identity);
  const identityCompany = safeObject(identity.company);
  const classification = safeObject(response.classification);
  const location = safeObject(response.location);
  const latestSnapshot = safeObject(response.latest_snapshot);
  const derivedMetrics = safeObject(response.derived_metrics);
  const sourceQuality = safeObject(response.source_quality);

  return {
    identity: {
      projectId: stringOrNull(identity.project_id) ?? fallbackId,
      canonicalName: stringOrNull(identity.canonical_name) ?? "Unnamed project",
      company: {
        id: stringOrNull(identityCompany.id) ?? "unknown-company",
        nameHe: stringOrNull(identityCompany.name_he) ?? "Unknown company",
      },
    },
    classification: {
      projectBusinessType: stringOrNull(classification.project_business_type) ?? "unknown",
      governmentProgramType: stringOrNull(classification.government_program_type) ?? "none",
      projectUrbanRenewalType: stringOrNull(classification.project_urban_renewal_type) ?? "none",
      projectStatus: stringOrNull(classification.project_status),
      permitStatus: stringOrNull(classification.permit_status),
      classificationConfidence: stringOrNull(classification.classification_confidence) ?? "low",
      trust: mapTrustMap(classification.trust),
    },
    location: {
      city: stringOrNull(location.city),
      neighborhood: stringOrNull(location.neighborhood),
      district: stringOrNull(location.district),
      locationConfidence: stringOrNull(location.location_confidence) ?? "unknown",
      locationQuality: stringOrNull(location.location_quality) ?? "unknown",
      trust: mapTrustMap(location.trust),
    },
    latestSnapshot: {
      snapshotId: stringOrNull(latestSnapshot.snapshot_id) ?? "",
      snapshotDate: stringOrNull(latestSnapshot.snapshot_date) ?? "",
      projectStatus: stringOrNull(latestSnapshot.project_status),
      permitStatus: stringOrNull(latestSnapshot.permit_status),
      totalUnits: numberOrNull(latestSnapshot.total_units),
      marketedUnits: numberOrNull(latestSnapshot.marketed_units),
      soldUnitsCumulative: numberOrNull(latestSnapshot.sold_units_cumulative),
      unsoldUnits: numberOrNull(latestSnapshot.unsold_units),
      avgPricePerSqmCumulative: numberOrNull(latestSnapshot.avg_price_per_sqm_cumulative),
      grossProfitTotalExpected: numberOrNull(latestSnapshot.gross_profit_total_expected),
      grossMarginExpectedPct: numberOrNull(latestSnapshot.gross_margin_expected_pct),
      trust: mapTrustMap(latestSnapshot.trust),
    },
    derivedMetrics: {
      sellThroughRate: numberOrNull(derivedMetrics.sell_through_rate),
      knownUnsoldUnits: numberOrNull(derivedMetrics.known_unsold_units),
      latestKnownAvgPricePerSqm: numberOrNull(derivedMetrics.latest_known_avg_price_per_sqm),
      knownMarginSignal: stringOrNull(derivedMetrics.known_margin_signal),
    },
    addresses: safeArray<Record<string, unknown>>(response.addresses).map(mapAddress),
    sourceQuality: {
      sourceCompany: stringOrNull(sourceQuality.source_company) ?? "Unknown company",
      sourceReportName: stringOrNull(sourceQuality.source_report_name),
      reportPeriodEnd: stringOrNull(sourceQuality.report_period_end) ?? "",
      publishedAt: stringOrNull(sourceQuality.published_at),
      sourceUrl: stringOrNull(sourceQuality.source_url) ?? "",
      sourcePages: stringOrNull(sourceQuality.source_pages),
      confidenceLevel: stringOrNull(sourceQuality.confidence_level) ?? "low",
      missingFields: safeArray<string>(sourceQuality.missing_fields).filter((value) => typeof value === "string"),
      valueOriginSummary: Object.fromEntries(
        Object.entries(safeObject(sourceQuality.value_origin_summary)).map(([key, rawValue]) => [
          key,
          numberOrNull(rawValue) ?? 0,
        ]),
      ),
    },
    fieldProvenance: safeArray<Record<string, unknown>>(response.field_provenance).map(mapFieldProvenance),
  };
}

export async function getProjects(filters: Record<string, string | undefined>) {
  const response = await apiFetch<{ items?: unknown[]; pagination?: { total?: number } }>("/api/v1/projects", {
    searchParams: buildSearchParams(filters),
  });
  const items = safeArray<Record<string, unknown>>(response?.items).map(mapProjectListItem);
  return {
    items,
    total: typeof response?.pagination?.total === "number" ? response.pagination.total : 0,
    state: response === null ? ("error" as const) : items.length > 0 ? ("ready" as const) : ("empty" as const),
  };
}

export async function getProjectDetail(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/projects/${id}`);
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }

  return { item: mapProjectDetail(response, id), state: "ready" as DataState };
}

export async function getProjectHistory(id: string) {
  const response = await apiFetch<{ snapshots?: unknown[] }>(`/api/v1/projects/${id}/history`);
  const items: ProjectHistoryItem[] = safeArray<Record<string, unknown>>(response?.snapshots).map((item, index) => ({
    snapshotId: stringOrNull(item.snapshot_id) ?? `snapshot-${index}`,
    snapshotDate: stringOrNull(item.snapshot_date) ?? "",
    reportId: stringOrNull(item.report_id) ?? "",
    reportPeriodEnd: stringOrNull(item.report_period_end),
    projectStatus: stringOrNull(item.project_status),
    permitStatus: stringOrNull(item.permit_status),
    totalUnits: numberOrNull(item.total_units),
    marketedUnits: numberOrNull(item.marketed_units),
    soldUnitsCumulative: numberOrNull(item.sold_units_cumulative),
    unsoldUnits: numberOrNull(item.unsold_units),
    avgPricePerSqmCumulative: numberOrNull(item.avg_price_per_sqm_cumulative),
    grossProfitTotalExpected: numberOrNull(item.gross_profit_total_expected),
    grossMarginExpectedPct: numberOrNull(item.gross_margin_expected_pct),
    sellThroughRate: numberOrNull(item.sell_through_rate),
    soldUnitsDelta: numberOrNull(item.sold_units_delta),
    unsoldUnitsDelta: numberOrNull(item.unsold_units_delta),
  }));

  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getCompanies(filters: Record<string, string | undefined> = {}) {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/companies", {
    searchParams: buildSearchParams(filters),
  });
  const items: CompanyListItem[] = safeArray<Record<string, unknown>>(response?.items).map((item, index) => ({
    id: stringOrNull(item.id) ?? `company-${index}`,
    nameHe: stringOrNull(item.name_he) ?? "Unknown company",
    ticker: stringOrNull(item.ticker),
    projectCount: numberOrNull(item.project_count) ?? 0,
    cityCount: numberOrNull(item.city_count) ?? 0,
    latestReportPeriodEnd: stringOrNull(item.latest_report_period_end),
    latestPublishedAt: stringOrNull(item.latest_published_at),
    knownUnsoldUnits: numberOrNull(item.known_unsold_units),
    projectsWithPreciseLocationCount: numberOrNull(item.projects_with_precise_location_count) ?? 0,
  }));

  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getCompanyDetail(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/companies/${id}`);
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }

  const kpis = safeObject(response.kpis);
  const item: CompanyDetail = {
    id: stringOrNull(response.id) ?? id,
    nameHe: stringOrNull(response.name_he) ?? "Unknown company",
    ticker: stringOrNull(response.ticker),
    latestReportName: stringOrNull(response.latest_report_name),
    latestReportPeriodEnd: stringOrNull(response.latest_report_period_end),
    latestPublishedAt: stringOrNull(response.latest_published_at),
    projectCount: numberOrNull(response.project_count) ?? 0,
    cityCount: numberOrNull(response.city_count) ?? 0,
    kpis: {
      knownUnsoldUnits: numberOrNull(kpis.known_unsold_units),
      projectsWithPreciseLocationCount: numberOrNull(kpis.projects_with_precise_location_count) ?? 0,
      companyCitySpread: numberOrNull(kpis.company_city_spread) ?? 0,
      latestKnownAvgPricePerSqm: numberOrNull(kpis.latest_known_avg_price_per_sqm),
    },
    cityCoverage: safeArray<Record<string, unknown>>(response.city_coverage).map((entry) => ({
      city: stringOrNull(entry.city) ?? "Unknown",
      projectCount: numberOrNull(entry.project_count) ?? 0,
    })),
    projectBusinessTypeDistribution: safeArray<Record<string, unknown>>(response.project_business_type_distribution).map((entry) => ({
      projectBusinessType: stringOrNull(entry.project_business_type) ?? "unknown",
      projectCount: numberOrNull(entry.project_count) ?? 0,
    })),
    projects: safeArray<Record<string, unknown>>(response.projects).map((entry, index) => ({
      id: stringOrNull(entry.id) ?? `project-${index}`,
      canonicalName: stringOrNull(entry.canonical_name) ?? "Unnamed project",
      city: stringOrNull(entry.city),
      projectBusinessType: stringOrNull(entry.project_business_type) ?? "unknown",
      projectStatus: stringOrNull(entry.project_status),
      permitStatus: stringOrNull(entry.permit_status),
      marketedUnits: numberOrNull(entry.marketed_units),
      soldUnitsCumulative: numberOrNull(entry.sold_units_cumulative),
      unsoldUnits: numberOrNull(entry.unsold_units),
      latestSnapshotDate: stringOrNull(entry.latest_snapshot_date),
      locationQuality: stringOrNull(entry.location_quality) ?? "unknown",
    })),
  };

  return { item, state: "ready" as DataState };
}

export async function getFiltersMetadata(): Promise<FiltersMetadata> {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/filters/metadata");
  return {
    companies: safeArray<Record<string, unknown>>(response?.companies).map((company) => ({
      id: stringOrNull(company.id),
      label: stringOrNull(company.label) ?? "Unknown company",
    })),
    cities: safeArray<string>(response?.cities).filter((value) => typeof value === "string"),
    projectBusinessTypes: safeArray<string>(response?.project_business_types).filter((value) => typeof value === "string"),
    governmentProgramTypes: safeArray<string>(response?.government_program_types).filter((value) => typeof value === "string"),
    projectUrbanRenewalTypes: safeArray<string>(response?.project_urban_renewal_types).filter((value) => typeof value === "string"),
    permitStatuses: safeArray<string>(response?.permit_statuses).filter((value) => typeof value === "string"),
  };
}

export async function getMapProjects(filters: Record<string, string | undefined>) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/map/projects", {
    searchParams: buildSearchParams(filters),
  });
  const features = safeArray<Record<string, unknown>>(response?.features).map((feature, index) => {
    const geometry = safeObject(feature.geometry);
    const properties = safeObject(feature.properties);
    const coordinates = Array.isArray(geometry.coordinates)
      ? geometry.coordinates.map((value) => numberOrNull(value))
      : [];
    return {
      type: "Feature" as const,
      geometry:
        typeof geometry.type === "string" &&
        coordinates.length === 2 &&
        coordinates.every((value) => typeof value === "number")
          ? { type: geometry.type, coordinates: coordinates as number[] }
          : null,
      properties: {
        projectId: stringOrNull(properties.project_id) ?? `map-project-${index}`,
        canonicalName: stringOrNull(properties.canonical_name) ?? "Unnamed project",
        companyName: stringOrNull(properties.company_name) ?? "Unknown company",
        city: stringOrNull(properties.city),
        projectBusinessType: stringOrNull(properties.project_business_type) ?? "unknown",
        projectStatus: stringOrNull(properties.project_status),
        avgPricePerSqmCumulative: numberOrNull(properties.avg_price_per_sqm_cumulative),
        unsoldUnits: numberOrNull(properties.unsold_units),
        locationConfidence: stringOrNull(properties.location_confidence) ?? "unknown",
        locationQuality: stringOrNull(properties.location_quality) ?? "unknown",
      },
    };
  });
  const meta = safeObject(response?.meta);
  const item: MapProjectsResponse = {
    features,
    meta: {
      availableProjects: numberOrNull(meta.available_projects) ?? 0,
      projectsWithCoordinates: numberOrNull(meta.projects_with_coordinates) ?? 0,
      locationQualityBreakdown: Object.fromEntries(
        Object.entries(safeObject(meta.location_quality_breakdown)).map(([key, rawValue]) => [key, numberOrNull(rawValue) ?? 0]),
      ),
    },
  };
  return {
    item,
    state: response === null ? ("error" as DataState) : features.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminProjects() {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/projects");
  const items: AdminProjectListItem[] = safeArray<Record<string, unknown>>(response?.items).map((item, index) => ({
    id: stringOrNull(item.id) ?? `admin-project-${index}`,
    canonicalName: stringOrNull(item.canonical_name) ?? "Unnamed project",
    company: {
      id: stringOrNull(safeObject(item.company).id) ?? "unknown-company",
      nameHe: stringOrNull(safeObject(item.company).name_he) ?? "Unknown company",
    },
    city: stringOrNull(item.city),
    projectBusinessType: stringOrNull(item.project_business_type) ?? "unknown",
    permitStatus: stringOrNull(item.permit_status),
    classificationConfidence: stringOrNull(item.classification_confidence) ?? "low",
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    needsAdminReview: Boolean(item.needs_admin_review),
    latestSnapshotDate: stringOrNull(item.latest_snapshot_date),
  }));
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminProjectDetail(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/projects/${id}`);
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }

  const classification = safeObject(response.classification);
  const location = safeObject(response.location);
  const latestSnapshot = safeObject(response.latest_snapshot);

  const item: AdminProjectDetail = {
    id: stringOrNull(response.id) ?? id,
    canonicalName: stringOrNull(response.canonical_name) ?? "Unnamed project",
    company: {
      id: stringOrNull(safeObject(response.company).id) ?? "unknown-company",
      nameHe: stringOrNull(safeObject(response.company).name_he) ?? "Unknown company",
    },
    classification: {
      projectBusinessType: stringOrNull(classification.project_business_type) ?? "unknown",
      governmentProgramType: stringOrNull(classification.government_program_type) ?? "none",
      projectUrbanRenewalType: stringOrNull(classification.project_urban_renewal_type) ?? "none",
      projectStatus: stringOrNull(classification.project_status),
      permitStatus: stringOrNull(classification.permit_status),
      classificationConfidence: stringOrNull(classification.classification_confidence) ?? "low",
      trust: mapTrustMap(classification.trust),
    },
    location: {
      city: stringOrNull(location.city),
      neighborhood: stringOrNull(location.neighborhood),
      district: stringOrNull(location.district),
      locationConfidence: stringOrNull(location.location_confidence) ?? "unknown",
      locationQuality: stringOrNull(location.location_quality) ?? "unknown",
      trust: mapTrustMap(location.trust),
    },
    latestSnapshot: {
      snapshotId: stringOrNull(latestSnapshot.snapshot_id) ?? "",
      snapshotDate: stringOrNull(latestSnapshot.snapshot_date) ?? "",
      projectStatus: stringOrNull(latestSnapshot.project_status),
      permitStatus: stringOrNull(latestSnapshot.permit_status),
      totalUnits: numberOrNull(latestSnapshot.total_units),
      marketedUnits: numberOrNull(latestSnapshot.marketed_units),
      soldUnitsCumulative: numberOrNull(latestSnapshot.sold_units_cumulative),
      unsoldUnits: numberOrNull(latestSnapshot.unsold_units),
      avgPricePerSqmCumulative: numberOrNull(latestSnapshot.avg_price_per_sqm_cumulative),
      grossProfitTotalExpected: numberOrNull(latestSnapshot.gross_profit_total_expected),
      grossMarginExpectedPct: numberOrNull(latestSnapshot.gross_margin_expected_pct),
      trust: mapTrustMap(latestSnapshot.trust),
    },
    addresses: safeArray<Record<string, unknown>>(response.addresses).map(mapAddress),
    fieldProvenance: safeArray<Record<string, unknown>>(response.field_provenance).map(mapFieldProvenance),
    notesInternal: stringOrNull(response.notes_internal),
    auditLog: safeArray<Record<string, unknown>>(response.audit_log).map((entry, index) => ({
      id: stringOrNull(entry.id) ?? `audit-${index}`,
      action: stringOrNull(entry.action) ?? "unknown",
      entityType: stringOrNull(entry.entity_type) ?? "unknown",
      entityId: stringOrNull(entry.entity_id),
      diffJson: entry.diff_json && typeof entry.diff_json === "object" ? (entry.diff_json as Record<string, unknown>) : null,
      comment: stringOrNull(entry.comment),
      createdAt: stringOrNull(entry.created_at) ?? "",
    })),
  };

  return { item, state: "ready" as DataState };
}

export async function updateAdminProject(
  id: string,
  payload: Record<string, unknown>,
): Promise<{ item: AdminProjectDetail | null; state: DataState }> {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/projects/${id}`, {
    method: "PATCH",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" };
  }
  return getAdminProjectDetail(id);
}

export async function upsertAdminProjectAddress(
  projectId: string,
  payload: Record<string, unknown>,
  addressId?: string,
): Promise<{ item: AdminProjectDetail | null; state: DataState }> {
  const path = addressId
    ? `/api/v1/admin/projects/${projectId}/addresses/${addressId}`
    : `/api/v1/admin/projects/${projectId}/addresses`;
  const response = await apiFetch<Record<string, unknown>>(path, {
    method: addressId ? "PUT" : "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" };
  }
  return getAdminProjectDetail(projectId);
}

export async function deleteAdminProjectAddress(
  projectId: string,
  addressId: string,
): Promise<{ item: AdminProjectDetail | null; state: DataState }> {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/projects/${projectId}/addresses/${addressId}`, {
    method: "DELETE",
  });
  if (response === null) {
    return { item: null, state: "error" };
  }
  return getAdminProjectDetail(projectId);
}

export async function getAdminReports() {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/reports");
  const items: AdminReportSummary[] = safeArray<Record<string, unknown>>(response?.items).map((item, index) => ({
    id: stringOrNull(item.id) ?? `report-${index}`,
    companyId: stringOrNull(item.company_id) ?? "unknown-company",
    companyNameHe: stringOrNull(item.company_name_he) ?? "Unknown company",
    reportName: stringOrNull(item.report_name),
    reportType: stringOrNull(item.report_type) ?? "unknown",
    periodType: stringOrNull(item.period_type) ?? "unknown",
    periodEndDate: stringOrNull(item.period_end_date) ?? "",
    publishedAt: stringOrNull(item.published_at),
    sourceUrl: stringOrNull(item.source_url),
    sourceFilePath: stringOrNull(item.source_file_path),
    sourceIsOfficial: Boolean(item.source_is_official),
    sourceLabel: stringOrNull(item.source_label),
    ingestionStatus: stringOrNull(item.ingestion_status) ?? "draft",
    notes: stringOrNull(item.notes),
    candidateCount: numberOrNull(item.candidate_count) ?? 0,
    createdAt: stringOrNull(item.created_at) ?? "",
    updatedAt: stringOrNull(item.updated_at) ?? "",
  }));
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function createAdminReport(payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/reports", {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminReportDetail(stringOrNull(response.id) ?? "");
}

export async function getAdminReportDetail(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/reports/${id}`);
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }

  const item: AdminReportDetail = {
    id: stringOrNull(response.id) ?? id,
    companyId: stringOrNull(response.company_id) ?? "unknown-company",
    companyNameHe: stringOrNull(response.company_name_he) ?? "Unknown company",
    reportName: stringOrNull(response.report_name),
    reportType: stringOrNull(response.report_type) ?? "unknown",
    periodType: stringOrNull(response.period_type) ?? "unknown",
    periodEndDate: stringOrNull(response.period_end_date) ?? "",
    publishedAt: stringOrNull(response.published_at),
    sourceUrl: stringOrNull(response.source_url),
    sourceFilePath: stringOrNull(response.source_file_path),
    sourceIsOfficial: Boolean(response.source_is_official),
    sourceLabel: stringOrNull(response.source_label),
    ingestionStatus: stringOrNull(response.ingestion_status) ?? "draft",
    notes: stringOrNull(response.notes),
    candidateCount: numberOrNull(response.candidate_count) ?? 0,
    createdAt: stringOrNull(response.created_at) ?? "",
    updatedAt: stringOrNull(response.updated_at) ?? "",
    stagingReportId: stringOrNull(response.staging_report_id) ?? "",
    stagingPublishStatus: stringOrNull(response.staging_publish_status) ?? "draft",
    stagingReviewStatus: stringOrNull(response.staging_review_status) ?? "pending",
    stagingNotesInternal: stringOrNull(response.staging_notes_internal),
    candidates: safeArray<Record<string, unknown>>(response.candidates).map(mapAdminCandidateSummary),
  };

  return { item, state: "ready" as DataState };
}

export async function updateAdminReport(id: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/reports/${id}`, {
    method: "PATCH",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminReportDetail(id);
}

export async function createAdminCandidate(reportId: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/reports/${reportId}/candidates`, {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminCandidateDetail(stringOrNull(response.id) ?? "");
}

export async function getAdminCandidateDetail(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/candidates/${id}`);
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }

  const item: AdminCandidateDetail = {
    id: stringOrNull(response.id) ?? id,
    stagingReportId: stringOrNull(response.staging_report_id) ?? "",
    reportId: stringOrNull(response.report_id) ?? "",
    companyId: stringOrNull(response.company_id) ?? "unknown-company",
    companyNameHe: stringOrNull(response.company_name_he) ?? "Unknown company",
    candidateProjectName: stringOrNull(response.candidate_project_name) ?? "Unnamed candidate",
    city: stringOrNull(response.city),
    neighborhood: stringOrNull(response.neighborhood),
    projectBusinessType: stringOrNull(response.project_business_type),
    governmentProgramType: stringOrNull(response.government_program_type) ?? "none",
    projectUrbanRenewalType: stringOrNull(response.project_urban_renewal_type) ?? "none",
    projectStatus: stringOrNull(response.project_status),
    permitStatus: stringOrNull(response.permit_status),
    totalUnits: numberOrNull(response.total_units),
    marketedUnits: numberOrNull(response.marketed_units),
    soldUnitsCumulative: numberOrNull(response.sold_units_cumulative),
    unsoldUnits: numberOrNull(response.unsold_units),
    avgPricePerSqmCumulative: numberOrNull(response.avg_price_per_sqm_cumulative),
    grossProfitTotalExpected: numberOrNull(response.gross_profit_total_expected),
    grossMarginExpectedPct: numberOrNull(response.gross_margin_expected_pct),
    locationConfidence: stringOrNull(response.location_confidence) ?? "unknown",
    valueOriginType: stringOrNull(response.value_origin_type) ?? "unknown",
    confidenceLevel: stringOrNull(response.confidence_level) ?? "low",
    matchingStatus: stringOrNull(response.matching_status) ?? "unmatched",
    publishStatus: stringOrNull(response.publish_status) ?? "draft",
    reviewStatus: stringOrNull(response.review_status) ?? "pending",
    reviewNotes: stringOrNull(response.review_notes),
    matchedProjectId: stringOrNull(response.matched_project_id),
    matchedProjectName: stringOrNull(response.matched_project_name),
    fieldCandidates: safeArray<Record<string, unknown>>(response.field_candidates).map(mapAdminFieldCandidate),
    addressCandidates: safeArray<Record<string, unknown>>(response.address_candidates).map(mapAdminAddressCandidate),
    matchSuggestions: safeArray<Record<string, unknown>>(response.match_suggestions).map(mapMatchSuggestion),
    compareRows: safeArray<Record<string, unknown>>(response.compare_rows).map(mapCandidateCompareRow),
    diffSummary: safeArray<Record<string, unknown>>(response.diff_summary).map(mapCandidateDiffItem),
    createdAt: stringOrNull(response.created_at) ?? "",
    updatedAt: stringOrNull(response.updated_at) ?? "",
  };

  return { item, state: "ready" as DataState };
}

export async function updateAdminCandidate(id: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/candidates/${id}`, {
    method: "PATCH",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminCandidateDetail(id);
}

export async function matchAdminCandidate(id: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/candidates/${id}/match`, {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminCandidateDetail(id);
}

export async function publishAdminCandidate(id: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/candidates/${id}/publish`, {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminCandidateDetail(id);
}

export async function getHomeKpis(): Promise<KpiDefinition[]> {
  const [projects, companies] = await Promise.all([getProjects({ page_size: "100" }), getCompanies()]);
  const totalUnsold = safeArray<ProjectListItem>(projects.items).reduce((sum, item) => sum + (item.unsoldUnits ?? 0), 0);

  return [
    {
      id: "projects",
      label: "Seeded public projects",
      value: String(projects.total),
      note: "Curated from the latest public report available for each of the five developers.",
    },
    {
      id: "unsold",
      label: "Known unsold units",
      value: String(totalUnsold),
      note: "Only reported values are counted. Missing values remain null.",
    },
    {
      id: "companies",
      label: "Covered public developers",
      value: String(companies.items.length),
      note: "Based on the five companies specified for the Phase 2 seed.",
    },
  ];
}
