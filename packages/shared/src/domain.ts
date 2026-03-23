export const PROJECT_BUSINESS_TYPES = [
  "regular_dev",
  "govt_program",
  "urban_renewal",
] as const;

export const GOVERNMENT_PROGRAM_TYPES = [
  "none",
  "mechir_lamishtaken",
  "mechir_metara",
  "dira_bahanaa",
  "other",
] as const;

export const URBAN_RENEWAL_TYPES = [
  "none",
  "pinui_binui",
  "tama_38_1",
  "tama_38_2",
  "other",
] as const;

export const LOCATION_CONFIDENCE_LEVELS = [
  "exact",
  "approximate",
  "city_only",
  "unknown",
] as const;

export const PROJECT_STATUSES = [
  "planning",
  "permit",
  "construction",
  "marketing",
  "completed",
  "stalled",
] as const;

export const PERMIT_STATUSES = [
  "none",
  "pending",
  "granted",
  "partial",
] as const;

export const CONFIDENCE_LEVELS = ["high", "medium", "low"] as const;
export const VALUE_ORIGIN_TYPES = ["reported", "inferred", "manual", "imported", "unknown"] as const;
export const REPORT_INGESTION_STATUSES = [
  "draft",
  "ready_for_staging",
  "in_review",
  "published",
  "rejected",
] as const;
export const MATCH_STATUSES = [
  "unmatched",
  "matched_existing_project",
  "new_project_needed",
  "ambiguous_match",
  "ignored",
] as const;
export const STAGING_PUBLISH_STATUSES = [
  "draft",
  "in_review",
  "partially_approved",
  "published",
  "rejected",
] as const;
export const MATCH_SUGGESTION_STATES = ["exact", "likely", "ambiguous", "no_match"] as const;

export type ProjectBusinessType = (typeof PROJECT_BUSINESS_TYPES)[number];
export type GovernmentProgramType = (typeof GOVERNMENT_PROGRAM_TYPES)[number];
export type UrbanRenewalType = (typeof URBAN_RENEWAL_TYPES)[number];
export type LocationConfidence = (typeof LOCATION_CONFIDENCE_LEVELS)[number];
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];
export type PermitStatus = (typeof PERMIT_STATUSES)[number];
export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];
export type ValueOriginType = (typeof VALUE_ORIGIN_TYPES)[number];
export type ReportIngestionStatus = (typeof REPORT_INGESTION_STATUSES)[number];
export type MatchStatus = (typeof MATCH_STATUSES)[number];
export type StagingPublishStatus = (typeof STAGING_PUBLISH_STATUSES)[number];
export type MatchSuggestionState = (typeof MATCH_SUGGESTION_STATES)[number];

export interface KpiDefinition {
  id: string;
  label: string;
  value: string;
  note?: string;
}

export interface PlaceholderProjectRow {
  canonicalName: string;
  companyName: string;
  city: string;
  projectBusinessType: ProjectBusinessType;
  status: ProjectStatus;
  locationConfidence: LocationConfidence;
}

export interface ApiPagination {
  page: number;
  pageSize: number;
  total: number;
}

export interface CompanyListItem {
  id: string;
  nameHe: string;
  ticker: string | null;
  projectCount: number;
  cityCount: number;
  latestReportPeriodEnd: string | null;
  latestPublishedAt: string | null;
  knownUnsoldUnits: number | null;
  projectsWithPreciseLocationCount: number;
}

export interface ProjectCompanySummary {
  id: string;
  nameHe: string;
}

export interface ProjectListItem {
  projectId: string;
  canonicalName: string;
  company: ProjectCompanySummary;
  city: string | null;
  neighborhood: string | null;
  projectBusinessType: ProjectBusinessType | string;
  governmentProgramType: GovernmentProgramType | string;
  projectUrbanRenewalType: UrbanRenewalType | string;
  projectStatus: ProjectStatus | string | null;
  permitStatus: string | null;
  totalUnits: number | null;
  marketedUnits: number | null;
  soldUnitsCumulative: number | null;
  unsoldUnits: number | null;
  avgPricePerSqmCumulative: number | null;
  grossProfitTotalExpected: number | null;
  grossMarginExpectedPct: number | null;
  latestSnapshotDate: string | null;
  locationConfidence: LocationConfidence | string;
  locationQuality: string;
  displayGeometryType: string;
  geometryIsManual: boolean;
  addressSummary: string | null;
  sellThroughRate: number | null;
}

export interface SelectOption {
  id: string | null;
  label: string;
}

export interface FiltersMetadata {
  companies: SelectOption[];
  cities: string[];
  projectBusinessTypes: string[];
  governmentProgramTypes: string[];
  projectUrbanRenewalTypes: string[];
  permitStatuses: string[];
  locationConfidences: string[];
}

export interface ValueTrust {
  valueOriginType: ValueOriginType | string;
  confidenceLevel: ConfidenceLevel | string;
}

export interface ProjectAddress {
  id: string;
  addressTextRaw: string | null;
  normalizedAddressText: string | null;
  city: string | null;
  normalizedCity: string | null;
  street: string | null;
  normalizedStreet: string | null;
  houseNumberFrom: number | null;
  houseNumberTo: number | null;
  parcelBlock: string | null;
  parcelNumber: string | null;
  subParcel: string | null;
  addressNote: string | null;
  lat: number | null;
  lng: number | null;
  locationConfidence: string;
  locationQuality: string;
  geometrySource: string;
  normalizedDisplayAddress: string | null;
  isGeocodingReady: boolean;
  geocodingStatus: string;
  geocodingMethod: string | null;
  geocodingProvider: string | null;
  geocodingSourceLabel: string | null;
  geocodingNote: string | null;
  isPrimary: boolean;
  valueOriginType: ValueOriginType | string;
}

export interface ProjectDisplayGeometry {
  geometryType: string;
  geometrySource: string;
  locationConfidence: string;
  locationQuality: string;
  geometryGeojson: Record<string, unknown> | null;
  centerLat: number | null;
  centerLng: number | null;
  addressSummary: string | null;
  note: string | null;
  cityOnly: boolean;
  hasCoordinates: boolean;
  isManualOverride: boolean;
  isSourceDerived: boolean;
}

export interface FieldProvenance {
  fieldName: string;
  rawValue: string | null;
  normalizedValue: string | null;
  sourcePage: number | null;
  sourceSection: string | null;
  extractionMethod: string;
  confidenceScore: number | null;
  valueOriginType: ValueOriginType | string;
  reviewStatus: string;
  reviewNote?: string | null;
}

export interface ProjectDetail {
  identity: {
    projectId: string;
    canonicalName: string;
    company: ProjectCompanySummary;
  };
  classification: {
    projectBusinessType: string;
    governmentProgramType: string;
    projectUrbanRenewalType: string;
    projectStatus: string | null;
    permitStatus: string | null;
    classificationConfidence: string;
    trust: Record<string, ValueTrust>;
  };
  location: {
    city: string | null;
    neighborhood: string | null;
    district: string | null;
    locationConfidence: string;
    locationQuality: string;
    addressSummary: string | null;
    trust: Record<string, ValueTrust>;
  };
  displayGeometry: ProjectDisplayGeometry;
  latestSnapshot: {
    snapshotId: string;
    snapshotDate: string;
    projectStatus: string | null;
    permitStatus: string | null;
    totalUnits: number | null;
    marketedUnits: number | null;
    soldUnitsCumulative: number | null;
    unsoldUnits: number | null;
    avgPricePerSqmCumulative: number | null;
    grossProfitTotalExpected: number | null;
    grossMarginExpectedPct: number | null;
    trust: Record<string, ValueTrust>;
  };
  derivedMetrics: {
    sellThroughRate: number | null;
    knownUnsoldUnits: number | null;
    latestKnownAvgPricePerSqm: number | null;
    knownMarginSignal: string | null;
  };
  addresses: ProjectAddress[];
  sourceQuality: {
    sourceCompany: string;
    sourceReportName: string | null;
    reportPeriodEnd: string;
    publishedAt: string | null;
    sourceUrl: string;
    sourcePages: string | null;
    confidenceLevel: string;
    missingFields: string[];
    valueOriginSummary: Record<string, number>;
  };
  fieldProvenance: FieldProvenance[];
}

export interface ProjectHistoryItem {
  snapshotId: string;
  snapshotDate: string;
  reportId: string;
  reportPeriodEnd: string | null;
  projectStatus: string | null;
  permitStatus: string | null;
  totalUnits: number | null;
  marketedUnits: number | null;
  soldUnitsCumulative: number | null;
  unsoldUnits: number | null;
  avgPricePerSqmCumulative: number | null;
  grossProfitTotalExpected: number | null;
  grossMarginExpectedPct: number | null;
  sellThroughRate: number | null;
  soldUnitsDelta: number | null;
  unsoldUnitsDelta: number | null;
}

export interface CompanyDetail {
  id: string;
  nameHe: string;
  ticker: string | null;
  latestReportName: string | null;
  latestReportPeriodEnd: string | null;
  latestPublishedAt: string | null;
  projectCount: number;
  cityCount: number;
  kpis: {
    knownUnsoldUnits: number | null;
    projectsWithPreciseLocationCount: number;
    companyCitySpread: number;
    latestKnownAvgPricePerSqm: number | null;
  };
  cityCoverage: Array<{ city: string; projectCount: number }>;
  projectBusinessTypeDistribution: Array<{ projectBusinessType: string; projectCount: number }>;
  projects: Array<{
    id: string;
    canonicalName: string;
    city: string | null;
    projectBusinessType: string;
    projectStatus: string | null;
    permitStatus: string | null;
    marketedUnits: number | null;
    soldUnitsCumulative: number | null;
    unsoldUnits: number | null;
    latestSnapshotDate: string | null;
    locationQuality: string;
  }>;
}

export interface MapFeatureItem {
  type: "Feature";
  geometry: Record<string, unknown> | null;
  properties: {
    projectId: string;
    canonicalName: string;
    companyId: string;
    companyName: string;
    city: string | null;
    neighborhood: string | null;
    projectBusinessType: string;
    governmentProgramType: string;
    projectUrbanRenewalType: string;
    projectStatus: string | null;
    permitStatus: string | null;
    totalUnits: number | null;
    marketedUnits: number | null;
    soldUnitsCumulative: number | null;
    avgPricePerSqmCumulative: number | null;
    unsoldUnits: number | null;
    grossProfitTotalExpected: number | null;
    grossMarginExpectedPct: number | null;
    latestSnapshotDate: string | null;
    geometryType: string;
    geometrySource: string;
    locationConfidence: string;
    locationQuality: string;
    addressSummary: string | null;
    centerLat: number | null;
    centerLng: number | null;
    cityOnly: boolean;
    hasCoordinates: boolean;
    geometryIsManual: boolean;
    isSourceDerived: boolean;
    reportedCount: number;
    inferredCount: number;
    manualCount: number;
  };
}

export interface MapProjectsResponse {
  features: MapFeatureItem[];
  meta: {
    availableProjects: number;
    projectsWithCoordinates: number;
    locationQualityBreakdown: Record<string, number>;
    geometryTypeBreakdown: Record<string, number>;
    cityOnlyProjects: number;
  };
}

export interface ExternalLayerSummary {
  id: string;
  layerName: string;
  sourceName: string;
  sourceUrl: string | null;
  geometryType: string;
  updateCadence: string;
  qualityScore: number | null;
  visibility: string;
  notes: string | null;
  isActive: boolean;
  defaultOnMap: boolean;
  recordCount: number;
}

export interface ExternalLayerFeatureItem {
  type: "Feature";
  geometry: Record<string, unknown> | null;
  properties: {
    layerId: string;
    layerName: string;
    sourceName: string;
    externalRecordId: string;
    label: string | null;
    city: string | null;
    effectiveDate: string | null;
    qualityScore: number | null;
    propertiesJson: Record<string, unknown>;
    relationCount: number;
  };
}

export interface MapExternalLayersResponse {
  features: ExternalLayerFeatureItem[];
  meta: {
    selectedLayers: number;
    selectedRecords: number;
    layerBreakdown: Record<string, number>;
  };
}

export interface AdminAuditLogItem {
  id: string;
  action: string;
  entityType: string;
  entityId: string | null;
  diffJson: Record<string, unknown> | null;
  comment: string | null;
  createdAt: string;
}

export interface AdminProjectListItem {
  id: string;
  canonicalName: string;
  company: ProjectCompanySummary;
  city: string | null;
  projectBusinessType: string;
  governmentProgramType: string;
  projectUrbanRenewalType: string;
  projectStatus: string | null;
  permitStatus: string | null;
  classificationConfidence: string;
  locationConfidence: string;
  needsAdminReview: boolean;
  latestSnapshotDate: string | null;
  sourceCount: number;
  addressCount: number;
  isPubliclyVisible: boolean;
  sourceConflictFlag: boolean;
}

export interface AdminProjectAliasItem {
  id: string;
  aliasName: string;
  valueOriginType: ValueOriginType | string;
  aliasSourceType: string;
  sourceReportId: string | null;
  isActive: boolean;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AdminProjectSourceItem {
  reportId: string;
  reportName: string | null;
  sourceLabel: string | null;
  sourceUrl: string | null;
  ingestionStatus: string;
  periodEndDate: string;
  publishedAt: string | null;
}

export interface AdminProjectLinkedCandidateItem {
  candidateId: string;
  candidateProjectName: string;
  matchingStatus: string;
  publishStatus: string;
  reviewStatus: string;
  sourceReportId: string;
  sourceReportName: string | null;
}

export interface AdminSnapshotSummary {
  id: string;
  reportId: string;
  reportName: string | null;
  snapshotDate: string;
  projectStatus: string | null;
  permitStatus: string | null;
  totalUnits: number | null;
  marketedUnits: number | null;
  soldUnitsCumulative: number | null;
  unsoldUnits: number | null;
  avgPricePerSqmCumulative: number | null;
  grossProfitTotalExpected: number | null;
  grossMarginExpectedPct: number | null;
  chronologyStatus: string;
  chronologyNotes: string | null;
  notesInternal: string | null;
  diffSummary: Record<string, { before: string | null; after: string | null; changed: boolean | null }>;
}

export interface AdminProjectDetail {
  id: string;
  canonicalName: string;
  company: ProjectCompanySummary;
  classification: ProjectDetail["classification"];
  location: ProjectDetail["location"];
  displayGeometry: ProjectDisplayGeometry;
  latestSnapshot: ProjectDetail["latestSnapshot"] | null;
  addresses: ProjectAddress[];
  aliases: AdminProjectAliasItem[];
  snapshots: AdminSnapshotSummary[];
  linkedSources: AdminProjectSourceItem[];
  linkedCandidates: AdminProjectLinkedCandidateItem[];
  fieldProvenance: FieldProvenance[];
  provenanceSummary: Record<string, number>;
  isPubliclyVisible: boolean;
  sourceConflictFlag: boolean;
  notesInternal: string | null;
  auditLog: AdminAuditLogItem[];
}

export interface AdminIntakeListItem {
  id: string;
  candidateProjectName: string;
  company: ProjectCompanySummary;
  city: string | null;
  sourceReportId: string;
  sourceReportName: string | null;
  matchingStatus: string;
  confidenceLevel: string;
  reviewStatus: string;
  publishStatus: string;
  matchedProjectId: string | null;
  matchedProjectName: string | null;
}

export interface AdminReportSummary {
  id: string;
  companyId: string;
  companyNameHe: string;
  reportName: string | null;
  reportType: string;
  periodType: string;
  periodEndDate: string;
  publishedAt: string | null;
  sourceUrl: string | null;
  sourceFilePath: string | null;
  sourceIsOfficial: boolean;
  sourceLabel: string | null;
  ingestionStatus: ReportIngestionStatus | string;
  notes: string | null;
  candidateCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface AdminCandidateSummary {
  id: string;
  candidateProjectName: string;
  city: string | null;
  neighborhood: string | null;
  matchingStatus: MatchStatus | string;
  publishStatus: StagingPublishStatus | string;
  confidenceLevel: ConfidenceLevel | string;
  reviewStatus: string;
  matchedProjectId: string | null;
  matchedProjectName: string | null;
  reviewNotes: string | null;
  diffSummary: Record<string, unknown> | null;
}

export interface AdminFieldCandidate {
  id: string;
  fieldName: string;
  rawValue: string | null;
  normalizedValue: string | null;
  sourcePage: number | null;
  sourceSection: string | null;
  valueOriginType: ValueOriginType | string;
  confidenceLevel: ConfidenceLevel | string;
  reviewStatus: string;
  reviewNotes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AdminAddressCandidate {
  id: string;
  addressTextRaw: string | null;
  street: string | null;
  houseNumberFrom: number | null;
  houseNumberTo: number | null;
  city: string | null;
  lat: number | null;
  lng: number | null;
  locationConfidence: string;
  isPrimary: boolean;
  valueOriginType: ValueOriginType | string;
  confidenceLevel: ConfidenceLevel | string;
  reviewStatus: string;
  reviewNotes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CandidateCompareRow {
  fieldName: string;
  canonicalValue: string | null;
  stagingValue: string | null;
  rawSourceValue: string | null;
  sourcePage: number | null;
  sourceSection: string | null;
  valueOriginType: ValueOriginType | string;
  confidenceLevel: ConfidenceLevel | string;
  changed: boolean;
}

export interface CandidateDiffItem {
  fieldName: string;
  previousValue: string | null;
  incomingValue: string | null;
  changed: boolean;
}

export interface MatchSuggestion {
  projectId: string;
  canonicalName: string;
  city: string | null;
  neighborhood: string | null;
  similarityScore: number;
  matchState: MatchSuggestionState | string;
  reasonsJson: Record<string, unknown>;
}

export interface AdminDuplicateSuggestion {
  id: string;
  projectId: string;
  projectName: string;
  duplicateProjectId: string;
  duplicateProjectName: string;
  companyName: string;
  city: string | null;
  duplicateCity: string | null;
  matchState: MatchSuggestionState | string;
  score: number;
  reasonsJson: Record<string, unknown>;
  reviewStatus: string;
}

export interface AdminCoverageCompany {
  companyId: string;
  companyNameHe: string;
  isActive: boolean;
  isInScope: boolean;
  outOfScopeReason: string | null;
  coveragePriority: string;
  latestReportRegisteredId: string | null;
  latestReportRegisteredName: string | null;
  latestReportPublished: string | null;
  latestReportIngestedId: string | null;
  latestReportIngestedName: string | null;
  historicalCoverageStart: string | null;
  historicalCoverageEnd: string | null;
  historicalCoverageStatus: string;
  backfillStatus: string;
  reportsRegistered: number;
  reportsPublishedIntoCanonical: number;
  projectsCreated: number;
  snapshotsCreated: number;
  projectsMissingKeyFields: number;
  projectsCityOnlyLocation: number;
  projectsWithExactOrApproximateGeometry: number;
  notes: string | null;
}

export interface AdminFieldCompletenessItem {
  fieldName: string;
  completeCount: number;
  missingCount: number;
}

export interface AdminCoverageDashboard {
  summary: {
    companiesInScope: number;
    companiesWithLatestReportIngested: number;
    companiesMissingLatestReport: number;
    reportsRegistered: number;
    reportsPublishedIntoCanonical: number;
    projectsCreated: number;
    snapshotsCreated: number;
    unmatchedCandidates: number;
    ambiguousCandidates: number;
    projectsMissingKeyFields: number;
    projectsCityOnlyLocation: number;
    projectsWithExactOrApproximateGeometry: number;
  };
  fieldCompleteness: AdminFieldCompletenessItem[];
  companies: AdminCoverageCompany[];
}

export interface AdminCoverageReportItem {
  reportId: string;
  companyId: string;
  companyNameHe: string;
  reportName: string | null;
  reportType: string;
  periodType: string;
  periodEndDate: string;
  publishedAt: string | null;
  isInScope: boolean;
  sourceIsOfficial: boolean;
  sourceLabel: string | null;
  sourceUrl: string | null;
  ingestionStatus: string;
  linkedProjectCount: number;
  linkedSnapshotCount: number;
  isPublishedIntoCanonical: boolean;
  isLatestRegistered: boolean;
  isLatestIngested: boolean;
}

export interface AdminCoverageGapItem {
  projectId: string;
  projectName: string;
  companyId: string;
  companyNameHe: string;
  city: string | null;
  locationConfidence: string;
  locationQuality: string;
  latestSnapshotDate: string | null;
  latestSnapshotAgeDays: number | null;
  missingFields: string[];
  sourceCount: number;
  addressCount: number;
  isPubliclyVisible: boolean;
  backfillStatus: string;
}

export interface AdminCoverageGapsResponse {
  summary: {
    totalItems: number;
    missingLocation: number;
    missingMetrics: number;
    staleOrMissingSnapshot: number;
  };
  items: AdminCoverageGapItem[];
}

export interface AdminLocationReviewItem {
  projectId: string;
  projectName: string;
  company: ProjectCompanySummary;
  city: string | null;
  neighborhood: string | null;
  locationConfidence: string;
  locationQuality: string;
  geometryType: string;
  geometrySource: string;
  geometryIsManual: boolean;
  addressCount: number;
  primaryAddressId: string | null;
  primaryAddressSummary: string | null;
  geocodingStatus: string | null;
  geocodingMethod: string | null;
  geocodingSourceLabel: string | null;
  isGeocodingReady: boolean;
  latestSnapshotDate: string | null;
  latestSnapshotAgeDays: number | null;
  backfillStatus: string;
  missingLocationFields: string[];
}

export interface AdminLocationReviewResponse {
  summary: {
    totalItems: number;
    cityOnly: number;
    unknown: number;
    manualGeometry: number;
    geocodingReady: number;
  };
  items: AdminLocationReviewItem[];
}

export interface AdminLocationReference {
  cities: string[];
  streets: string[];
}

export interface AdminParserRun {
  id: string;
  reportId: string;
  stagingReportId: string | null;
  status: string;
  parserVersion: string;
  sourceLabel: string | null;
  sourceReference: string | null;
  sourceChecksum: string | null;
  sectionsFound: number;
  candidateCount: number;
  fieldCandidateCount: number;
  addressCandidateCount: number;
  warnings: string[];
  errors: string[];
  diagnostics: Record<string, unknown>;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AdminAnomalyItem {
  id: string;
  anomalyType: string;
  severity: string;
  projectId: string;
  projectName: string;
  companyName: string;
  snapshotId: string | null;
  reportId: string | null;
  sourceReportName: string | null;
  summary: string;
  detailsJson: Record<string, unknown>;
}

export interface AdminOpsDashboard {
  summary: {
    reportsRegistered: number;
    projectsCreated: number;
    snapshotsCreated: number;
    openAnomalies: number;
    parserFailedRuns: number;
    readyToPublish: number;
  };
  ingestionHealth: Record<string, unknown>;
  matchingBacklog: Record<string, number>;
  publishBacklog: Record<string, number>;
  coverageCompleteness: Record<string, number>;
  locationCompleteness: Record<string, unknown>;
  parserHealth: Record<string, unknown>;
  topAnomalies: AdminAnomalyItem[];
}

export interface AdminExternalLayerListItem {
  id: string;
  layerName: string;
  sourceName: string;
  sourceUrl: string | null;
  geometryType: string;
  updateCadence: string;
  qualityScore: number | null;
  visibility: string;
  notes: string | null;
  isActive: boolean;
  defaultOnMap: boolean;
  recordCount: number;
  relationCount: number;
  updatedAt: string;
}

export interface AdminExternalLayerRecordItem {
  id: string;
  externalRecordId: string;
  label: string | null;
  city: string | null;
  effectiveDate: string | null;
  propertiesJson: Record<string, unknown>;
  updateMetadata: Record<string, unknown> | null;
  relationCount: number;
}

export interface AdminExternalLayerDetail extends AdminExternalLayerListItem {
  records: AdminExternalLayerRecordItem[];
  relationMethodBreakdown: Record<string, number>;
}

export interface AdminCandidateDetail {
  id: string;
  stagingReportId: string;
  reportId: string;
  companyId: string;
  companyNameHe: string;
  candidateProjectName: string;
  city: string | null;
  neighborhood: string | null;
  projectBusinessType: string | null;
  governmentProgramType: string;
  projectUrbanRenewalType: string;
  projectStatus: string | null;
  permitStatus: string | null;
  totalUnits: number | null;
  marketedUnits: number | null;
  soldUnitsCumulative: number | null;
  unsoldUnits: number | null;
  avgPricePerSqmCumulative: number | null;
  grossProfitTotalExpected: number | null;
  grossMarginExpectedPct: number | null;
  locationConfidence: string;
  valueOriginType: ValueOriginType | string;
  confidenceLevel: ConfidenceLevel | string;
  matchingStatus: MatchStatus | string;
  publishStatus: StagingPublishStatus | string;
  reviewStatus: string;
  reviewNotes: string | null;
  matchedProjectId: string | null;
  matchedProjectName: string | null;
  fieldCandidates: AdminFieldCandidate[];
  addressCandidates: AdminAddressCandidate[];
  matchSuggestions: MatchSuggestion[];
  compareRows: CandidateCompareRow[];
  diffSummary: CandidateDiffItem[];
  createdAt: string;
  updatedAt: string;
}

export interface AdminReportDetail extends AdminReportSummary {
  stagingReportId: string;
  stagingPublishStatus: StagingPublishStatus | string;
  stagingReviewStatus: string;
  stagingNotesInternal: string | null;
  candidates: AdminCandidateSummary[];
}
