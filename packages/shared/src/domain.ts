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

export type ProjectBusinessType = (typeof PROJECT_BUSINESS_TYPES)[number];
export type GovernmentProgramType = (typeof GOVERNMENT_PROGRAM_TYPES)[number];
export type UrbanRenewalType = (typeof URBAN_RENEWAL_TYPES)[number];
export type LocationConfidence = (typeof LOCATION_CONFIDENCE_LEVELS)[number];
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

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
