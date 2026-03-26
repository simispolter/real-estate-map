import type {
  AdminAddressCandidate,
  AdminCandidateDetail,
  AdminCandidateSummary,
  AdminAnomalyItem,
  AdminCoverageDashboard,
  AdminCoverageGapItem,
  AdminCoverageGapsResponse,
  AdminCoverageReportItem,
  AdminCoverageCompany,
  AdminDuplicateSuggestion,
  AdminExternalLayerDetail,
  AdminExternalLayerListItem,
  AdminFieldCandidate,
  AdminIntakeListItem,
  AdminOpsDashboard,
  AdminParserRun,
  AdminReportQa,
  AdminProjectAliasItem,
  AdminProjectDetail,
  AdminProjectListItem,
  AdminProjectLinkedCandidateItem,
  AdminLocationReviewItem,
  AdminLocationReviewResponse,
  AdminLocationReference,
  AdminProjectSourceItem,
  AdminReportDetail,
  AdminReportSummary,
  AdminSnapshotSummary,
  CandidateCompareRow,
  CandidateDiffItem,
  CompanyDetail,
  CompanyListItem,
  ExternalLayerSummary,
  FieldProvenance,
  FiltersMetadata,
  KpiDefinition,
  MatchSuggestion,
  MapExternalLayersResponse,
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
  cache?: RequestCache;
  revalidateSeconds?: number | false;
  logLabel?: string;
};

type NextFetchOptions = {
  revalidate?: number;
  tags?: string[];
};

function getApiBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_BASE_URL ?? "http://api:8000";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

function isServerRuntime() {
  return typeof window === "undefined";
}

function inferRevalidateSeconds(path: string): number {
  if (path === "/api/v1/filters/metadata" || path === "/api/v1/map/layers" || path === "/api/v1/map/layers/features") {
    return 300;
  }
  if (path === "/api/v1/map/projects") {
    return 60;
  }
  if (path.startsWith("/api/v1/projects/") || path.startsWith("/api/v1/companies/")) {
    return 120;
  }
  if (path === "/api/v1/projects" || path === "/api/v1/companies") {
    return 90;
  }
  return 60;
}

function resolveFetchBehavior(path: string, options: ApiOptions): { cache?: RequestCache; next?: NextFetchOptions } {
  const isReadRequest = (options.method ?? "GET") === "GET" && !options.body;
  if (!isReadRequest || path.startsWith("/api/v1/admin")) {
    return { cache: "no-store" };
  }
  if (!isServerRuntime()) {
    return { cache: options.cache ?? "default" };
  }

  if (options.revalidateSeconds === false) {
    return { cache: "no-store" };
  }

  const revalidateSeconds =
    typeof options.revalidateSeconds === "number" ? options.revalidateSeconds : inferRevalidateSeconds(path);
  return { next: { revalidate: revalidateSeconds } };
}

function logServerFetchTiming(label: string, path: string, durationMs: number, ok: boolean) {
  if (!isServerRuntime()) {
    return;
  }

  console.info(`[web-fetch] ${label} path=${path} duration_ms=${durationMs} ok=${ok}`);
}

export function logServerPageTiming(label: string, startedAt: number, meta?: Record<string, string | number | null | undefined>) {
  if (!isServerRuntime()) {
    return;
  }

  const durationMs = Date.now() - startedAt;
  const details =
    meta && Object.keys(meta).length > 0
      ? ` ${Object.entries(meta)
          .filter(([, value]) => value !== undefined)
          .map(([key, value]) => `${key}=${String(value)}`)
          .join(" ")}`
      : "";
  console.info(`[web-page] ${label} duration_ms=${durationMs}${details}`);
}

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T | null> {
  const query = options.searchParams && options.searchParams.toString() ? `?${options.searchParams.toString()}` : "";
  const apiBaseUrl = getApiBaseUrl();
  const startedAt = Date.now();
  const fetchBehavior = resolveFetchBehavior(path, options);

  try {
    const response = await fetch(`${apiBaseUrl}${path}${query}`, {
      method: options.method ?? "GET",
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: fetchBehavior.cache,
      next: fetchBehavior.next,
    });
    if (options.logLabel) {
      logServerFetchTiming(options.logLabel, `${path}${query}`, Date.now() - startedAt, response.ok);
    }
    if (!response.ok) {
      return null;
    }
    if (response.status === 204) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    if (options.logLabel) {
      logServerFetchTiming(options.logLabel, `${path}${query}`, Date.now() - startedAt, false);
    }
    return null;
  }
}

function safeArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function safeObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function mapExtensionBlocks(value: unknown): Record<string, Record<string, unknown>> {
  const source = safeObject(value);
  return Object.fromEntries(
    Object.entries(source).map(([key, raw]) => [key, safeObject(raw)]),
  );
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
    lifecycleStage: stringOrNull(item.lifecycle_stage),
    disclosureLevel: stringOrNull(item.disclosure_level),
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
    displayGeometryType: stringOrNull(item.display_geometry_type) ?? "unknown",
    geometryIsManual: Boolean(item.geometry_is_manual),
    addressSummary: stringOrNull(item.address_summary),
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
    normalizedAddressText: stringOrNull(item.normalized_address_text),
    city: stringOrNull(item.city),
    normalizedCity: stringOrNull(item.normalized_city),
    street: stringOrNull(item.street),
    normalizedStreet: stringOrNull(item.normalized_street),
    houseNumberFrom: numberOrNull(item.house_number_from),
    houseNumberTo: numberOrNull(item.house_number_to),
    parcelBlock: stringOrNull(item.parcel_block),
    parcelNumber: stringOrNull(item.parcel_number),
    subParcel: stringOrNull(item.sub_parcel),
    addressNote: stringOrNull(item.address_note),
    lat: numberOrNull(item.lat),
    lng: numberOrNull(item.lng),
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    locationQuality: stringOrNull(item.location_quality) ?? "unknown",
    geometrySource: stringOrNull(item.geometry_source) ?? "unknown",
    normalizedDisplayAddress: stringOrNull(item.normalized_display_address),
    isGeocodingReady: Boolean(item.is_geocoding_ready),
    geocodingStatus: stringOrNull(item.geocoding_status) ?? "not_started",
    geocodingMethod: stringOrNull(item.geocoding_method),
    geocodingProvider: stringOrNull(item.geocoding_provider),
    geocodingSourceLabel: stringOrNull(item.geocoding_source_label),
    geocodingNote: stringOrNull(item.geocoding_note),
    isPrimary: Boolean(item.is_primary),
    valueOriginType: stringOrNull(item.value_origin_type) ?? "unknown",
  };
}

function mapDisplayGeometry(item: Record<string, unknown>) {
  return {
    geometryType: stringOrNull(item.geometry_type) ?? "unknown",
    geometrySource: stringOrNull(item.geometry_source) ?? "unknown",
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    locationQuality: stringOrNull(item.location_quality) ?? "unknown",
    geometryGeojson: item.geometry_geojson && typeof item.geometry_geojson === "object"
      ? (item.geometry_geojson as Record<string, unknown>)
      : null,
    centerLat: numberOrNull(item.center_lat),
    centerLng: numberOrNull(item.center_lng),
    addressSummary: stringOrNull(item.address_summary),
    note: stringOrNull(item.note),
    cityOnly: Boolean(item.city_only),
    hasCoordinates: Boolean(item.has_coordinates),
    isManualOverride: Boolean(item.is_manual_override),
    isSourceDerived: Boolean(item.is_source_derived),
  };
}

function mapExternalLayerSummary(item: Record<string, unknown>, index: number): ExternalLayerSummary {
  return {
    id: stringOrNull(item.id) ?? `layer-${index}`,
    layerName: stringOrNull(item.layer_name) ?? "Unnamed layer",
    sourceName: stringOrNull(item.source_name) ?? "Unknown source",
    sourceUrl: stringOrNull(item.source_url),
    geometryType: stringOrNull(item.geometry_type) ?? "point",
    updateCadence: stringOrNull(item.update_cadence) ?? "ad_hoc",
    qualityScore: numberOrNull(item.quality_score),
    visibility: stringOrNull(item.visibility) ?? "public",
    notes: stringOrNull(item.notes),
    isActive: typeof item.is_active === "boolean" ? item.is_active : true,
    defaultOnMap: typeof item.default_on_map === "boolean" ? item.default_on_map : false,
    recordCount: numberOrNull(item.record_count) ?? 0,
  };
}

function mapAdminExternalLayer(item: Record<string, unknown>, index: number): AdminExternalLayerListItem {
  return {
    ...mapExternalLayerSummary(item, index),
    relationCount: numberOrNull(item.relation_count) ?? 0,
    updatedAt: stringOrNull(item.updated_at) ?? "",
  };
}

function mapAdminProjectAlias(item: Record<string, unknown>, index: number): AdminProjectAliasItem {
  return {
    id: stringOrNull(item.id) ?? `alias-${index}`,
    aliasName: stringOrNull(item.alias_name) ?? "",
    valueOriginType: stringOrNull(item.value_origin_type) ?? "unknown",
    aliasSourceType: stringOrNull(item.alias_source_type) ?? "manual",
    sourceReportId: stringOrNull(item.source_report_id),
    isActive: typeof item.is_active === "boolean" ? item.is_active : true,
    notes: stringOrNull(item.notes),
    createdAt: stringOrNull(item.created_at) ?? "",
    updatedAt: stringOrNull(item.updated_at) ?? "",
  };
}

function mapAdminProjectSource(item: Record<string, unknown>, index: number): AdminProjectSourceItem {
  return {
    reportId: stringOrNull(item.report_id) ?? `report-${index}`,
    reportName: stringOrNull(item.report_name),
    sourceLabel: stringOrNull(item.source_label),
    sourceUrl: stringOrNull(item.source_url),
    ingestionStatus: stringOrNull(item.ingestion_status) ?? "draft",
    periodEndDate: stringOrNull(item.period_end_date) ?? "",
    publishedAt: stringOrNull(item.published_at),
  };
}

function mapAdminLinkedCandidate(item: Record<string, unknown>, index: number): AdminProjectLinkedCandidateItem {
  return {
    candidateId: stringOrNull(item.candidate_id) ?? `candidate-${index}`,
    candidateProjectName: stringOrNull(item.candidate_project_name) ?? "Unnamed candidate",
    matchingStatus: stringOrNull(item.matching_status) ?? "unmatched",
    publishStatus: stringOrNull(item.publish_status) ?? "draft",
    reviewStatus: stringOrNull(item.review_status) ?? "pending",
    sourceReportId: stringOrNull(item.source_report_id) ?? "",
    sourceReportName: stringOrNull(item.source_report_name),
  };
}

function mapAdminSnapshotSummary(item: Record<string, unknown>, index: number): AdminSnapshotSummary {
  const diffSummary = safeObject(item.diff_summary);
  return {
    id: stringOrNull(item.id) ?? `snapshot-${index}`,
    reportId: stringOrNull(item.report_id) ?? "",
    reportName: stringOrNull(item.report_name),
    snapshotDate: stringOrNull(item.snapshot_date) ?? "",
    lifecycleStage: stringOrNull(item.lifecycle_stage),
    disclosureLevel: stringOrNull(item.disclosure_level),
    sourceSectionKind: stringOrNull(item.source_section_kind),
    projectStatus: stringOrNull(item.project_status),
    permitStatus: stringOrNull(item.permit_status),
    totalUnits: numberOrNull(item.total_units),
    marketedUnits: numberOrNull(item.marketed_units),
    soldUnitsCumulative: numberOrNull(item.sold_units_cumulative),
    unsoldUnits: numberOrNull(item.unsold_units),
    avgPricePerSqmCumulative: numberOrNull(item.avg_price_per_sqm_cumulative),
    grossProfitTotalExpected: numberOrNull(item.gross_profit_total_expected),
    grossMarginExpectedPct: numberOrNull(item.gross_margin_expected_pct),
    chronologyStatus: stringOrNull(item.chronology_status) ?? "ok",
    chronologyNotes: stringOrNull(item.chronology_notes),
    notesInternal: stringOrNull(item.notes_internal),
    extensionBlocks: mapExtensionBlocks(item.extension_blocks),
    diffSummary: Object.fromEntries(
      Object.entries(diffSummary).map(([fieldName, raw]) => {
        const rawObject = safeObject(raw);
        return [
          fieldName,
          {
            before: stringOrNull(rawObject.before),
            after: stringOrNull(rawObject.after),
            changed: typeof rawObject.changed === "boolean" ? rawObject.changed : null,
          },
        ];
      }),
    ),
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
    sourceTableName: stringOrNull(item.source_table_name),
    sourceRowLabel: stringOrNull(item.source_row_label),
    extractionProfileKey: stringOrNull(item.extraction_profile_key),
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
    candidateLifecycleStage: stringOrNull(item.candidate_lifecycle_stage),
    candidateDisclosureLevel: stringOrNull(item.candidate_disclosure_level),
    candidateSectionKind: stringOrNull(item.candidate_section_kind),
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
    matchState: stringOrNull(item.match_state) ?? "no_match",
    reasonsJson: safeObject(item.reasons_json),
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
  const displayGeometry = safeObject(response.display_geometry);

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
      lifecycleStage: stringOrNull(classification.lifecycle_stage),
      disclosureLevel: stringOrNull(classification.disclosure_level),
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
      addressSummary: stringOrNull(location.address_summary),
      trust: mapTrustMap(location.trust),
    },
    displayGeometry: mapDisplayGeometry(displayGeometry),
    latestSnapshot: {
      snapshotId: stringOrNull(latestSnapshot.snapshot_id) ?? "",
      snapshotDate: stringOrNull(latestSnapshot.snapshot_date) ?? "",
      lifecycleStage: stringOrNull(latestSnapshot.lifecycle_stage),
      disclosureLevel: stringOrNull(latestSnapshot.disclosure_level),
      sourceSectionKind: stringOrNull(latestSnapshot.source_section_kind),
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
      extensionBlocks: mapExtensionBlocks(latestSnapshot.extension_blocks),
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
    logLabel: "projects-list",
  });
  const items = safeArray<Record<string, unknown>>(response?.items).map(mapProjectListItem);
  return {
    items,
    total: typeof response?.pagination?.total === "number" ? response.pagination.total : 0,
    state: response === null ? ("error" as const) : items.length > 0 ? ("ready" as const) : ("empty" as const),
  };
}

export async function getProjectDetail(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/projects/${id}`, {
    logLabel: "project-detail",
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }

  return { item: mapProjectDetail(response, id), state: "ready" as DataState };
}

export async function getProjectHistory(id: string) {
  const response = await apiFetch<{ snapshots?: unknown[] }>(`/api/v1/projects/${id}/history`, {
    logLabel: "project-history",
  });
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
    logLabel: "companies-list",
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
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/companies/${id}`, {
    logLabel: "company-detail",
  });
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
  const response = await apiFetch<Record<string, unknown>>("/api/v1/filters/metadata", {
    logLabel: "filters-metadata",
  });
  return {
    companies: safeArray<Record<string, unknown>>(response?.companies).map((company) => ({
      id: stringOrNull(company.id),
      label: stringOrNull(company.label) ?? "Unknown company",
    })),
    cities: safeArray<string>(response?.cities).filter((value) => typeof value === "string"),
    lifecycleStages: safeArray<string>(response?.lifecycle_stages).filter((value) => typeof value === "string"),
    disclosureLevels: safeArray<string>(response?.disclosure_levels).filter((value) => typeof value === "string"),
    projectBusinessTypes: safeArray<string>(response?.project_business_types).filter((value) => typeof value === "string"),
    governmentProgramTypes: safeArray<string>(response?.government_program_types).filter((value) => typeof value === "string"),
    projectUrbanRenewalTypes: safeArray<string>(response?.project_urban_renewal_types).filter((value) => typeof value === "string"),
    projectStatuses: safeArray<string>(response?.project_statuses).filter((value) => typeof value === "string"),
    permitStatuses: safeArray<string>(response?.permit_statuses).filter((value) => typeof value === "string"),
    locationConfidences: safeArray<string>(response?.location_confidences).filter((value) => typeof value === "string"),
  };
}

export async function getMapProjects(filters: Record<string, string | undefined>) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/map/projects", {
    searchParams: buildSearchParams(filters),
    logLabel: "map-projects",
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
        companyId: stringOrNull(properties.company_id) ?? "unknown-company",
        companyName: stringOrNull(properties.company_name) ?? "Unknown company",
        city: stringOrNull(properties.city),
        neighborhood: stringOrNull(properties.neighborhood),
        lifecycleStage: stringOrNull(properties.lifecycle_stage),
        disclosureLevel: stringOrNull(properties.disclosure_level),
        projectBusinessType: stringOrNull(properties.project_business_type) ?? "unknown",
        governmentProgramType: stringOrNull(properties.government_program_type) ?? "none",
        projectUrbanRenewalType: stringOrNull(properties.project_urban_renewal_type) ?? "none",
        projectStatus: stringOrNull(properties.project_status),
        permitStatus: stringOrNull(properties.permit_status),
        totalUnits: numberOrNull(properties.total_units),
        marketedUnits: numberOrNull(properties.marketed_units),
        soldUnitsCumulative: numberOrNull(properties.sold_units_cumulative),
        avgPricePerSqmCumulative: numberOrNull(properties.avg_price_per_sqm_cumulative),
        unsoldUnits: numberOrNull(properties.unsold_units),
        grossProfitTotalExpected: numberOrNull(properties.gross_profit_total_expected),
        grossMarginExpectedPct: numberOrNull(properties.gross_margin_expected_pct),
        latestSnapshotDate: stringOrNull(properties.latest_snapshot_date),
        locationConfidence: stringOrNull(properties.location_confidence) ?? "unknown",
        locationQuality: stringOrNull(properties.location_quality) ?? "unknown",
        geometryType: stringOrNull(properties.geometry_type) ?? "unknown",
        geometrySource: stringOrNull(properties.geometry_source) ?? "unknown",
        addressSummary: stringOrNull(properties.address_summary),
        centerLat: numberOrNull(properties.center_lat),
        centerLng: numberOrNull(properties.center_lng),
        cityOnly: Boolean(properties.city_only),
        hasCoordinates: Boolean(properties.has_coordinates),
        geometryIsManual: Boolean(properties.geometry_is_manual),
        isSourceDerived: Boolean(properties.is_source_derived),
        reportedCount: numberOrNull(properties.reported_count) ?? 0,
        inferredCount: numberOrNull(properties.inferred_count) ?? 0,
        manualCount: numberOrNull(properties.manual_count) ?? 0,
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
      geometryTypeBreakdown: Object.fromEntries(
        Object.entries(safeObject(meta.geometry_type_breakdown)).map(([key, rawValue]) => [key, numberOrNull(rawValue) ?? 0]),
      ),
      cityOnlyProjects: numberOrNull(meta.city_only_projects) ?? 0,
    },
  };
  return {
    item,
    state: response === null ? ("error" as DataState) : features.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getMapLayers() {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/map/layers", {
    logLabel: "map-layers",
  });
  const items = safeArray<Record<string, unknown>>(response?.items).map(mapExternalLayerSummary);
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getMapExternalLayers(layerIds: string[], filters: Record<string, string | undefined>) {
  const searchParams = buildSearchParams({ city: filters.city });
  if (layerIds.length > 0) {
    searchParams.set("layer_ids", layerIds.join(","));
  }
  const response = await apiFetch<Record<string, unknown>>("/api/v1/map/layers/features", {
    searchParams,
    logLabel: "map-external-layers",
  });
  const features = safeArray<Record<string, unknown>>(response?.features).map((feature, index) => {
    const geometry = safeObject(feature.geometry);
    const properties = safeObject(feature.properties);
    return {
      type: "Feature" as const,
      geometry: Object.keys(geometry).length > 0 ? geometry : null,
      properties: {
        layerId: stringOrNull(properties.layer_id) ?? `layer-${index}`,
        layerName: stringOrNull(properties.layer_name) ?? "Unnamed layer",
        sourceName: stringOrNull(properties.source_name) ?? "Unknown source",
        externalRecordId: stringOrNull(properties.external_record_id) ?? `record-${index}`,
        label: stringOrNull(properties.label),
        city: stringOrNull(properties.city),
        effectiveDate: stringOrNull(properties.effective_date),
        qualityScore: numberOrNull(properties.quality_score),
        propertiesJson: safeObject(properties.properties_json),
        relationCount: numberOrNull(properties.relation_count) ?? 0,
      },
    };
  });
  const meta = safeObject(response?.meta);
  const item: MapExternalLayersResponse = {
    features,
    meta: {
      selectedLayers: numberOrNull(meta.selected_layers) ?? 0,
      selectedRecords: numberOrNull(meta.selected_records) ?? 0,
      layerBreakdown: Object.fromEntries(
        Object.entries(safeObject(meta.layer_breakdown)).map(([key, rawValue]) => [key, numberOrNull(rawValue) ?? 0]),
      ),
    },
  };
  return {
    item,
    state: response === null ? ("error" as DataState) : features.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminProjects(filters: Record<string, string | undefined> = {}) {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/projects", {
    searchParams: buildSearchParams(filters),
  });
  const items: AdminProjectListItem[] = safeArray<Record<string, unknown>>(response?.items).map((item, index) => ({
    id: stringOrNull(item.id) ?? `admin-project-${index}`,
    canonicalName: stringOrNull(item.canonical_name) ?? "Unnamed project",
    company: {
      id: stringOrNull(safeObject(item.company).id) ?? "unknown-company",
      nameHe: stringOrNull(safeObject(item.company).name_he) ?? "Unknown company",
    },
    city: stringOrNull(item.city),
    lifecycleStage: stringOrNull(item.lifecycle_stage),
    disclosureLevel: stringOrNull(item.disclosure_level),
    projectBusinessType: stringOrNull(item.project_business_type) ?? "unknown",
    governmentProgramType: stringOrNull(item.government_program_type) ?? "none",
    projectUrbanRenewalType: stringOrNull(item.project_urban_renewal_type) ?? "none",
    projectStatus: stringOrNull(item.project_status),
    permitStatus: stringOrNull(item.permit_status),
    classificationConfidence: stringOrNull(item.classification_confidence) ?? "low",
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    needsAdminReview: Boolean(item.needs_admin_review),
    latestSnapshotDate: stringOrNull(item.latest_snapshot_date),
    sourceCount: numberOrNull(item.source_count) ?? 0,
    addressCount: numberOrNull(item.address_count) ?? 0,
    isPubliclyVisible: Boolean(item.is_publicly_visible),
    sourceConflictFlag: Boolean(item.source_conflict_flag),
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
  const displayGeometry = safeObject(response.display_geometry);

  const item: AdminProjectDetail = {
    id: stringOrNull(response.id) ?? id,
    canonicalName: stringOrNull(response.canonical_name) ?? "Unnamed project",
    company: {
      id: stringOrNull(safeObject(response.company).id) ?? "unknown-company",
      nameHe: stringOrNull(safeObject(response.company).name_he) ?? "Unknown company",
    },
    classification: {
      lifecycleStage: stringOrNull(classification.lifecycle_stage),
      disclosureLevel: stringOrNull(classification.disclosure_level),
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
      addressSummary: stringOrNull(location.address_summary),
      trust: mapTrustMap(location.trust),
    },
    displayGeometry: mapDisplayGeometry(displayGeometry),
    latestSnapshot:
      Object.keys(latestSnapshot).length > 0
        ? {
            snapshotId: stringOrNull(latestSnapshot.snapshot_id) ?? "",
            snapshotDate: stringOrNull(latestSnapshot.snapshot_date) ?? "",
            lifecycleStage: stringOrNull(latestSnapshot.lifecycle_stage),
            disclosureLevel: stringOrNull(latestSnapshot.disclosure_level),
            sourceSectionKind: stringOrNull(latestSnapshot.source_section_kind),
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
            extensionBlocks: mapExtensionBlocks(latestSnapshot.extension_blocks),
          }
        : null,
    addresses: safeArray<Record<string, unknown>>(response.addresses).map(mapAddress),
    aliases: safeArray<Record<string, unknown>>(response.aliases).map(mapAdminProjectAlias),
    snapshots: safeArray<Record<string, unknown>>(response.snapshots).map(mapAdminSnapshotSummary),
    linkedSources: safeArray<Record<string, unknown>>(response.linked_sources).map(mapAdminProjectSource),
    linkedCandidates: safeArray<Record<string, unknown>>(response.linked_candidates).map(mapAdminLinkedCandidate),
    fieldProvenance: safeArray<Record<string, unknown>>(response.field_provenance).map(mapFieldProvenance),
    provenanceSummary: Object.fromEntries(
      Object.entries(safeObject(response.provenance_summary)).map(([key, value]) => [key, numberOrNull(value) ?? 0]),
    ),
    isPubliclyVisible: Boolean(response.is_publicly_visible),
    sourceConflictFlag: Boolean(response.source_conflict_flag),
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

export async function createAdminProject(payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/projects", {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminProjectDetail(stringOrNull(response.id) ?? "");
}

export async function addAdminProjectAlias(projectId: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/projects/${projectId}/aliases`, {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminProjectDetail(projectId);
}

export async function deleteAdminProjectAlias(projectId: string, aliasId: string, reviewerNote?: string) {
  const searchParams = new URLSearchParams();
  if (reviewerNote) {
    searchParams.set("reviewer_note", reviewerNote);
  }
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/projects/${projectId}/aliases/${aliasId}`, {
    method: "DELETE",
    searchParams,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminProjectDetail(projectId);
}

export async function createAdminProjectSnapshot(projectId: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/projects/${projectId}/snapshots`, {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminProjectDetail(projectId);
}

export async function updateAdminSnapshot(snapshotId: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/snapshots/${snapshotId}`, {
    method: "PATCH",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  const projectId = stringOrNull(response.id);
  return projectId ? getAdminProjectDetail(projectId) : { item: null, state: "error" as DataState };
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

export async function normalizeAdminProjectAddress(projectId: string, addressId: string) {
  const response = await apiFetch<Record<string, unknown>>(
    `/api/v1/admin/projects/${projectId}/addresses/${addressId}/normalize`,
    {
      method: "POST",
    },
  );
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminProjectDetail(projectId);
}

export async function geocodeAdminProjectAddress(projectId: string, addressId: string) {
  const response = await apiFetch<Record<string, unknown>>(
    `/api/v1/admin/projects/${projectId}/addresses/${addressId}/geocode`,
    {
      method: "POST",
    },
  );
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminProjectDetail(projectId);
}

export async function updateAdminProjectDisplayGeometry(projectId: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/projects/${projectId}/display-geometry`, {
    method: "PATCH",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
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

export async function runAdminReportExtraction(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/reports/${id}/extract`, {
    method: "POST",
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminReportDetail(id);
}

export async function getAdminReportParserRuns(reportId: string) {
  const response = await apiFetch<{ items?: unknown[] }>(`/api/v1/admin/reports/${reportId}/parser-runs`);
  const items = safeArray<Record<string, unknown>>(response?.items).map(mapAdminParserRun);
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminReportQa(reportId: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/reports/${reportId}/qa`);
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return { item: mapAdminReportQa(response), state: "ready" as DataState };
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
    candidateLifecycleStage: stringOrNull(response.candidate_lifecycle_stage),
    candidateDisclosureLevel: stringOrNull(response.candidate_disclosure_level),
    candidateSectionKind: stringOrNull(response.candidate_section_kind),
    candidateMaterialityFlag:
      typeof response.candidate_materiality_flag === "boolean" ? response.candidate_materiality_flag : null,
    sourceTableName: stringOrNull(response.source_table_name),
    sourceRowLabel: stringOrNull(response.source_row_label),
    extractionProfileKey: stringOrNull(response.extraction_profile_key),
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
    extensionBlocks: mapExtensionBlocks(response.extension_blocks),
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

export async function getAdminIntake(filters: Record<string, string | undefined> = {}) {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/intake", {
    searchParams: buildSearchParams(filters),
  });
  const items: AdminIntakeListItem[] = safeArray<Record<string, unknown>>(response?.items).map((item, index) => ({
    id: stringOrNull(item.id) ?? `intake-${index}`,
    candidateProjectName: stringOrNull(item.candidate_project_name) ?? "Unnamed candidate",
    company: {
      id: stringOrNull(safeObject(item.company).id) ?? "unknown-company",
      nameHe: stringOrNull(safeObject(item.company).name_he) ?? "Unknown company",
    },
    city: stringOrNull(item.city),
    sourceReportId: stringOrNull(item.source_report_id) ?? "",
    sourceReportName: stringOrNull(item.source_report_name),
    matchingStatus: stringOrNull(item.matching_status) ?? "unmatched",
    confidenceLevel: stringOrNull(item.confidence_level) ?? "low",
    reviewStatus: stringOrNull(item.review_status) ?? "pending",
    publishStatus: stringOrNull(item.publish_status) ?? "draft",
    matchedProjectId: stringOrNull(item.matched_project_id),
    matchedProjectName: stringOrNull(item.matched_project_name),
  }));
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminDuplicates() {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/duplicates");
  const items: AdminDuplicateSuggestion[] = safeArray<Record<string, unknown>>(response?.items).map((item, index) => ({
    id: stringOrNull(item.id) ?? `duplicate-${index}`,
    projectId: stringOrNull(item.project_id) ?? "",
    projectName: stringOrNull(item.project_name) ?? "Unknown project",
    duplicateProjectId: stringOrNull(item.duplicate_project_id) ?? "",
    duplicateProjectName: stringOrNull(item.duplicate_project_name) ?? "Unknown project",
    companyName: stringOrNull(item.company_name) ?? "Unknown company",
    city: stringOrNull(item.city),
    duplicateCity: stringOrNull(item.duplicate_city),
    matchState: stringOrNull(item.match_state) ?? "no_match",
    score: numberOrNull(item.score) ?? 0,
    reasonsJson: safeObject(item.reasons_json),
    reviewStatus: stringOrNull(item.review_status) ?? "open",
  }));
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function mergeAdminProjects(payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/projects/merge", {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminProjectDetail(stringOrNull(response.id) ?? "");
}

function mapCoverageCompany(item: Record<string, unknown>, index: number): AdminCoverageCompany {
  return {
    companyId: stringOrNull(item.company_id) ?? `coverage-${index}`,
    companyNameHe: stringOrNull(item.company_name_he) ?? "Unknown company",
    isActive: typeof item.is_active === "boolean" ? item.is_active : true,
    isInScope: Boolean(item.is_in_scope),
    outOfScopeReason: stringOrNull(item.out_of_scope_reason),
    coveragePriority: stringOrNull(item.coverage_priority) ?? "medium",
    latestReportRegisteredId: stringOrNull(item.latest_report_registered_id),
    latestReportRegisteredName: stringOrNull(item.latest_report_registered_name),
    latestReportPublished: stringOrNull(item.latest_report_published),
    latestReportIngestedId: stringOrNull(item.latest_report_ingested_id),
    latestReportIngestedName: stringOrNull(item.latest_report_ingested_name),
    historicalCoverageStart: stringOrNull(item.historical_coverage_start),
    historicalCoverageEnd: stringOrNull(item.historical_coverage_end),
    historicalCoverageStatus: stringOrNull(item.historical_coverage_status) ?? "not_started",
    backfillStatus: stringOrNull(item.backfill_status) ?? "not_started",
    reportsRegistered: numberOrNull(item.reports_registered) ?? 0,
    reportsPublishedIntoCanonical: numberOrNull(item.reports_published_into_canonical) ?? 0,
    projectsCreated: numberOrNull(item.projects_created) ?? 0,
    snapshotsCreated: numberOrNull(item.snapshots_created) ?? 0,
    projectsMissingKeyFields: numberOrNull(item.projects_missing_key_fields) ?? 0,
    projectsCityOnlyLocation: numberOrNull(item.projects_city_only_location) ?? 0,
    projectsWithExactOrApproximateGeometry:
      numberOrNull(item.projects_with_exact_or_approximate_geometry) ?? 0,
    notes: stringOrNull(item.notes),
  };
}

function mapAdminCoverageReport(item: Record<string, unknown>, index: number): AdminCoverageReportItem {
  return {
    reportId: stringOrNull(item.report_id) ?? `coverage-report-${index}`,
    companyId: stringOrNull(item.company_id) ?? "",
    companyNameHe: stringOrNull(item.company_name_he) ?? "Unknown company",
    reportName: stringOrNull(item.report_name),
    reportType: stringOrNull(item.report_type) ?? "unknown",
    periodType: stringOrNull(item.period_type) ?? "unknown",
    periodEndDate: stringOrNull(item.period_end_date) ?? "",
    publishedAt: stringOrNull(item.published_at),
    isInScope: typeof item.is_in_scope === "boolean" ? item.is_in_scope : true,
    sourceIsOfficial: typeof item.source_is_official === "boolean" ? item.source_is_official : false,
    sourceLabel: stringOrNull(item.source_label),
    sourceUrl: stringOrNull(item.source_url),
    ingestionStatus: stringOrNull(item.ingestion_status) ?? "draft",
    linkedProjectCount: numberOrNull(item.linked_project_count) ?? 0,
    linkedSnapshotCount: numberOrNull(item.linked_snapshot_count) ?? 0,
    isPublishedIntoCanonical: Boolean(item.is_published_into_canonical),
    isLatestRegistered: Boolean(item.is_latest_registered),
    isLatestIngested: Boolean(item.is_latest_ingested),
  };
}

function mapAdminCoverageGap(item: Record<string, unknown>, index: number): AdminCoverageGapItem {
  return {
    projectId: stringOrNull(item.project_id) ?? `gap-${index}`,
    projectName: stringOrNull(item.project_name) ?? "Unknown project",
    companyId: stringOrNull(item.company_id) ?? "",
    companyNameHe: stringOrNull(item.company_name_he) ?? "Unknown company",
    city: stringOrNull(item.city),
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    locationQuality: stringOrNull(item.location_quality) ?? "unknown",
    latestSnapshotDate: stringOrNull(item.latest_snapshot_date),
    latestSnapshotAgeDays: numberOrNull(item.latest_snapshot_age_days),
    missingFields: safeArray<string>(item.missing_fields).filter((value) => typeof value === "string"),
    sourceCount: numberOrNull(item.source_count) ?? 0,
    addressCount: numberOrNull(item.address_count) ?? 0,
    isPubliclyVisible: Boolean(item.is_publicly_visible),
    backfillStatus: stringOrNull(item.backfill_status) ?? "not_started",
  };
}

function mapAdminLocationReviewItem(item: Record<string, unknown>, index: number): AdminLocationReviewItem {
  const company = safeObject(item.company);
  return {
    projectId: stringOrNull(item.project_id) ?? `location-${index}`,
    projectName: stringOrNull(item.project_name) ?? "Unknown project",
    company: {
      id: stringOrNull(company.id) ?? "",
      nameHe: stringOrNull(company.name_he) ?? "Unknown company",
    },
    city: stringOrNull(item.city),
    neighborhood: stringOrNull(item.neighborhood),
    locationConfidence: stringOrNull(item.location_confidence) ?? "unknown",
    locationQuality: stringOrNull(item.location_quality) ?? "unknown",
    geometryType: stringOrNull(item.geometry_type) ?? "unknown",
    geometrySource: stringOrNull(item.geometry_source) ?? "unknown",
    geometryIsManual: Boolean(item.geometry_is_manual),
    addressCount: numberOrNull(item.address_count) ?? 0,
    primaryAddressId: stringOrNull(item.primary_address_id),
    primaryAddressSummary: stringOrNull(item.primary_address_summary),
    geocodingStatus: stringOrNull(item.geocoding_status),
    geocodingMethod: stringOrNull(item.geocoding_method),
    geocodingSourceLabel: stringOrNull(item.geocoding_source_label),
    isGeocodingReady: Boolean(item.is_geocoding_ready),
    latestSnapshotDate: stringOrNull(item.latest_snapshot_date),
    latestSnapshotAgeDays: numberOrNull(item.latest_snapshot_age_days),
    backfillStatus: stringOrNull(item.backfill_status) ?? "not_started",
    missingLocationFields: safeArray<string>(item.missing_location_fields).filter((value) => typeof value === "string"),
  };
}

function mapAdminParserRun(item: Record<string, unknown>, index: number): AdminParserRun {
  return {
    id: stringOrNull(item.id) ?? `parser-run-${index}`,
    reportId: stringOrNull(item.report_id) ?? "",
    stagingReportId: stringOrNull(item.staging_report_id),
    status: stringOrNull(item.status) ?? "failed",
    parserVersion: stringOrNull(item.parser_version) ?? "unknown",
    sourceLabel: stringOrNull(item.source_label),
    sourceReference: stringOrNull(item.source_reference),
    sourceChecksum: stringOrNull(item.source_checksum),
    sectionsFound: numberOrNull(item.sections_found) ?? 0,
    candidateCount: numberOrNull(item.candidate_count) ?? 0,
    fieldCandidateCount: numberOrNull(item.field_candidate_count) ?? 0,
    addressCandidateCount: numberOrNull(item.address_candidate_count) ?? 0,
    warnings: safeArray<string>(item.warnings),
    errors: safeArray<string>(item.errors),
    diagnostics: safeObject(item.diagnostics),
    startedAt: stringOrNull(item.started_at),
    finishedAt: stringOrNull(item.finished_at),
    createdAt: stringOrNull(item.created_at) ?? "",
    updatedAt: stringOrNull(item.updated_at) ?? "",
  };
}

function mapAdminReportQa(item: Record<string, unknown>): AdminReportQa {
  const summary = safeObject(item.summary);
  return {
    reportId: stringOrNull(item.report_id) ?? "",
    summary: {
      totalCandidates: numberOrNull(summary.total_candidates) ?? 0,
      extractedCandidates: numberOrNull(summary.extracted_candidates) ?? 0,
      manualCandidates: numberOrNull(summary.manual_candidates) ?? 0,
      projectsDetected: numberOrNull(summary.projects_detected) ?? 0,
      matchedExistingProjects: numberOrNull(summary.matched_existing_projects) ?? 0,
      newProjectsNeeded: numberOrNull(summary.new_projects_needed) ?? 0,
      newCanonicalProjectsCreated: numberOrNull(summary.new_canonical_projects_created) ?? 0,
      ambiguousCandidates: numberOrNull(summary.ambiguous_candidates) ?? 0,
      rejectedOrIgnoredCandidates: numberOrNull(summary.rejected_or_ignored_candidates) ?? 0,
      publishedCandidates: numberOrNull(summary.published_candidates) ?? 0,
      unresolvedPendingCandidates: numberOrNull(summary.unresolved_pending_candidates) ?? 0,
      missingKeyFieldTotal: numberOrNull(summary.missing_key_field_total) ?? 0,
      latestParserSectionsFound: numberOrNull(summary.latest_parser_sections_found) ?? 0,
      latestParserCandidateCount: numberOrNull(summary.latest_parser_candidate_count) ?? 0,
    },
    lifecycleStageDistribution: safeArray<Record<string, unknown>>(item.lifecycle_stage_distribution).map(
      (row, index) => ({
        key: stringOrNull(row.key) ?? `lifecycle-${index}`,
        count: numberOrNull(row.count) ?? 0,
      }),
    ),
    disclosureLevelDistribution: safeArray<Record<string, unknown>>(item.disclosure_level_distribution).map(
      (row, index) => ({
        key: stringOrNull(row.key) ?? `disclosure-${index}`,
        count: numberOrNull(row.count) ?? 0,
      }),
    ),
    familyCoverage: safeArray<Record<string, unknown>>(item.family_coverage).map((row, index) => ({
      sectionKind: stringOrNull(row.section_kind) ?? `family-${index}`,
      sectionCount: numberOrNull(row.section_count) ?? 0,
      candidateCount: numberOrNull(row.candidate_count) ?? 0,
      matchedExistingCount: numberOrNull(row.matched_existing_count) ?? 0,
      newProjectCount: numberOrNull(row.new_project_count) ?? 0,
      ambiguousCount: numberOrNull(row.ambiguous_count) ?? 0,
      ignoredCount: numberOrNull(row.ignored_count) ?? 0,
    })),
    missingKeyFields: safeArray<Record<string, unknown>>(item.missing_key_fields).map((row, index) => ({
      fieldName: stringOrNull(row.field_name) ?? `field-${index}`,
      missingCount: numberOrNull(row.missing_count) ?? 0,
    })),
    latestParserRun:
      item.latest_parser_run && typeof item.latest_parser_run === "object"
        ? mapAdminParserRun(item.latest_parser_run as Record<string, unknown>, 0)
        : null,
  };
}

function mapAdminAnomalyItem(item: Record<string, unknown>, index: number): AdminAnomalyItem {
  return {
    id: stringOrNull(item.id) ?? `anomaly-${index}`,
    anomalyType: stringOrNull(item.anomaly_type) ?? "unknown",
    severity: stringOrNull(item.severity) ?? "low",
    projectId: stringOrNull(item.project_id) ?? "",
    projectName: stringOrNull(item.project_name) ?? "Unknown project",
    companyName: stringOrNull(item.company_name) ?? "Unknown company",
    snapshotId: stringOrNull(item.snapshot_id),
    reportId: stringOrNull(item.report_id),
    sourceReportName: stringOrNull(item.source_report_name),
    summary: stringOrNull(item.summary) ?? "Anomaly detected",
    detailsJson: safeObject(item.details_json),
  };
}

export async function getAdminCoverage() {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/coverage");
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  const summary = safeObject(response.summary);
  const item: AdminCoverageDashboard = {
    summary: {
      companiesInScope: numberOrNull(summary.companies_in_scope) ?? 0,
      companiesWithLatestReportIngested: numberOrNull(summary.companies_with_latest_report_ingested) ?? 0,
      companiesMissingLatestReport: numberOrNull(summary.companies_missing_latest_report) ?? 0,
      reportsRegistered: numberOrNull(summary.reports_registered) ?? 0,
      reportsPublishedIntoCanonical: numberOrNull(summary.reports_published_into_canonical) ?? 0,
      projectsCreated: numberOrNull(summary.projects_created) ?? 0,
      snapshotsCreated: numberOrNull(summary.snapshots_created) ?? 0,
      unmatchedCandidates: numberOrNull(summary.unmatched_candidates) ?? 0,
      ambiguousCandidates: numberOrNull(summary.ambiguous_candidates) ?? 0,
      projectsMissingKeyFields: numberOrNull(summary.projects_missing_key_fields) ?? 0,
      projectsCityOnlyLocation: numberOrNull(summary.projects_city_only_location) ?? 0,
      projectsWithExactOrApproximateGeometry:
        numberOrNull(summary.projects_with_exact_or_approximate_geometry) ?? 0,
    },
    fieldCompleteness: safeArray<Record<string, unknown>>(response.field_completeness).map((item, index) => ({
      fieldName: stringOrNull(item.field_name) ?? `field-${index}`,
      completeCount: numberOrNull(item.complete_count) ?? 0,
      missingCount: numberOrNull(item.missing_count) ?? 0,
    })),
    companies: safeArray<Record<string, unknown>>(response.companies).map(mapCoverageCompany),
  };
  return { item, state: "ready" as DataState };
}

export async function getAdminCoverageReports(filters: Record<string, string | undefined> = {}) {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/coverage/reports", {
    searchParams: buildSearchParams(filters),
  });
  const items = safeArray<Record<string, unknown>>(response?.items).map(mapAdminCoverageReport);
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminCoverageGaps(filters: Record<string, string | undefined> = {}) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/coverage/gaps", {
    searchParams: buildSearchParams(filters),
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  const summary = safeObject(response.summary);
  const item: AdminCoverageGapsResponse = {
    summary: {
      totalItems: numberOrNull(summary.total_items) ?? 0,
      missingLocation: numberOrNull(summary.missing_location) ?? 0,
      missingMetrics: numberOrNull(summary.missing_metrics) ?? 0,
      staleOrMissingSnapshot: numberOrNull(summary.stale_or_missing_snapshot) ?? 0,
    },
    items: safeArray<Record<string, unknown>>(response.items).map(mapAdminCoverageGap),
  };
  return { item, state: "ready" as DataState };
}

export async function getAdminLocationReview(filters: Record<string, string | undefined> = {}) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/location-review/projects", {
    searchParams: buildSearchParams(filters),
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  const summary = safeObject(response.summary);
  const item: AdminLocationReviewResponse = {
    summary: {
      totalItems: numberOrNull(summary.total_items) ?? 0,
      cityOnly: numberOrNull(summary.city_only) ?? 0,
      unknown: numberOrNull(summary.unknown) ?? 0,
      manualGeometry: numberOrNull(summary.manual_geometry) ?? 0,
      geocodingReady: numberOrNull(summary.geocoding_ready) ?? 0,
    },
    items: safeArray<Record<string, unknown>>(response.items).map(mapAdminLocationReviewItem),
  };
  return { item, state: "ready" as DataState };
}

export async function getAdminLocationReference(filters: Record<string, string | undefined> = {}) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/location-reference", {
    searchParams: buildSearchParams(filters),
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  const item: AdminLocationReference = {
    cities: safeArray<string>(response.cities).filter((value) => typeof value === "string"),
    streets: safeArray<string>(response.streets).filter((value) => typeof value === "string"),
  };
  return { item, state: "ready" as DataState };
}

export async function applyAdminCoverageBulk(payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/coverage/bulk", {
    method: "POST",
    body: payload,
  });
  return {
    item: response
      ? {
          appliedCount: numberOrNull(response.applied_count) ?? 0,
          targetType: stringOrNull(response.target_type) ?? "company",
          action: stringOrNull(response.action) ?? "set_scope",
        }
      : null,
    state: response === null ? ("error" as DataState) : ("ready" as DataState),
  };
}

export async function getAdminAnomalies() {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/anomalies");
  const items = safeArray<Record<string, unknown>>(response?.items).map(mapAdminAnomalyItem);
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminOps() {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/ops");
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  const summary = safeObject(response.summary);
  const item: AdminOpsDashboard = {
    summary: {
      reportsRegistered: numberOrNull(summary.reports_registered) ?? 0,
      projectsCreated: numberOrNull(summary.projects_created) ?? 0,
      snapshotsCreated: numberOrNull(summary.snapshots_created) ?? 0,
      openAnomalies: numberOrNull(summary.open_anomalies) ?? 0,
      parserFailedRuns: numberOrNull(summary.parser_failed_runs) ?? 0,
      readyToPublish: numberOrNull(summary.ready_to_publish) ?? 0,
    },
    ingestionHealth: safeObject(response.ingestion_health),
    matchingBacklog: Object.fromEntries(
      Object.entries(safeObject(response.matching_backlog)).map(([key, value]) => [key, numberOrNull(value) ?? 0]),
    ),
    publishBacklog: Object.fromEntries(
      Object.entries(safeObject(response.publish_backlog)).map(([key, value]) => [key, numberOrNull(value) ?? 0]),
    ),
    coverageCompleteness: Object.fromEntries(
      Object.entries(safeObject(response.coverage_completeness)).map(([key, value]) => [key, numberOrNull(value) ?? 0]),
    ),
    locationCompleteness: safeObject(response.location_completeness),
    parserHealth: safeObject(response.parser_health),
    topAnomalies: safeArray<Record<string, unknown>>(response.top_anomalies).map(mapAdminAnomalyItem),
  };
  return { item, state: "ready" as DataState };
}

export async function getAdminLayers() {
  const response = await apiFetch<{ items?: unknown[] }>("/api/v1/admin/layers");
  const items = safeArray<Record<string, unknown>>(response?.items).map(mapAdminExternalLayer);
  return {
    items,
    state: response === null ? ("error" as DataState) : items.length > 0 ? ("ready" as DataState) : ("empty" as DataState),
  };
}

export async function getAdminLayerDetail(id: string) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/layers/${id}`);
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  const base = mapAdminExternalLayer(response, 0);
  const item: AdminExternalLayerDetail = {
    ...base,
    records: safeArray<Record<string, unknown>>(response.records).map((record, index) => ({
      id: stringOrNull(record.id) ?? `layer-record-${index}`,
      externalRecordId: stringOrNull(record.external_record_id) ?? `record-${index}`,
      label: stringOrNull(record.label),
      city: stringOrNull(record.city),
      effectiveDate: stringOrNull(record.effective_date),
      propertiesJson: safeObject(record.properties_json),
      updateMetadata: record.update_metadata && typeof record.update_metadata === "object"
        ? (record.update_metadata as Record<string, unknown>)
        : null,
      relationCount: numberOrNull(record.relation_count) ?? 0,
    })),
    relationMethodBreakdown: Object.fromEntries(
      Object.entries(safeObject(response.relation_method_breakdown)).map(([key, value]) => [key, numberOrNull(value) ?? 0]),
    ),
  };
  return { item, state: "ready" as DataState };
}

export async function createAdminLayer(payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/admin/layers", {
    method: "POST",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminLayerDetail(stringOrNull(response.id) ?? "");
}

export async function updateAdminLayer(id: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/layers/${id}`, {
    method: "PATCH",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminLayerDetail(id);
}

export async function updateAdminCoverage(companyId: string, payload: Record<string, unknown>) {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/admin/coverage/${companyId}`, {
    method: "PATCH",
    body: payload,
  });
  if (response === null) {
    return { item: null, state: "error" as DataState };
  }
  return getAdminCoverage();
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
