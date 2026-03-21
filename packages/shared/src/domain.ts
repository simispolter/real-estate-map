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
  "street",
  "neighborhood",
  "city",
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
}

export interface ValueTrust {
  valueOriginType: ValueOriginType | string;
  confidenceLevel: ConfidenceLevel | string;
}

export interface ProjectAddress {
  id: string;
  addressTextRaw: string | null;
  city: string | null;
  street: string | null;
  houseNumberFrom: number | null;
  houseNumberTo: number | null;
  lat: number | null;
  lng: number | null;
  locationConfidence: string;
  locationQuality: string;
  isPrimary: boolean;
  valueOriginType: ValueOriginType | string;
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
    trust: Record<string, ValueTrust>;
  };
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
  geometry: { type: string; coordinates: number[] } | null;
  properties: {
    projectId: string;
    canonicalName: string;
    companyName: string;
    city: string | null;
    projectBusinessType: string;
    projectStatus: string | null;
    avgPricePerSqmCumulative: number | null;
    unsoldUnits: number | null;
    locationConfidence: string;
    locationQuality: string;
  };
}

export interface MapProjectsResponse {
  features: MapFeatureItem[];
  meta: {
    availableProjects: number;
    projectsWithCoordinates: number;
    locationQualityBreakdown: Record<string, number>;
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
  permitStatus: string | null;
  classificationConfidence: string;
  locationConfidence: string;
  needsAdminReview: boolean;
  latestSnapshotDate: string | null;
}

export interface AdminProjectDetail {
  id: string;
  canonicalName: string;
  company: ProjectCompanySummary;
  classification: ProjectDetail["classification"];
  location: ProjectDetail["location"];
  latestSnapshot: ProjectDetail["latestSnapshot"];
  addresses: ProjectAddress[];
  fieldProvenance: FieldProvenance[];
  notesInternal: string | null;
  auditLog: AdminAuditLogItem[];
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
