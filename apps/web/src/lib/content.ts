import type { KpiDefinition, PlaceholderProjectRow } from "@real-estat-map/shared";

export const publicNavigation = [
  { href: "/", label: "Overview" },
  { href: "/projects", label: "Projects" },
  { href: "/companies", label: "Companies" },
  { href: "/admin", label: "Admin" },
];

export const adminNavigation = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin#reports", label: "Reports Queue" },
  { href: "/admin#review", label: "Review Queue" },
  { href: "/admin#location", label: "Location Assignment" },
  { href: "/admin#publish", label: "Publish Center" },
];

export const homeKpis: KpiDefinition[] = [
  {
    id: "projects",
    label: "Published residential projects",
    value: "--",
    note: "Populates once published snapshots are available.",
  },
  {
    id: "unsold",
    label: "Unsold units surfaced",
    value: "--",
    note: "Derived from the latest canonical project snapshots.",
  },
  {
    id: "companies",
    label: "Public companies covered",
    value: "--",
    note: "Company coverage expands after ingestion lands in Sprint 2.",
  },
];

export const companyKpis: KpiDefinition[] = [
  {
    id: "pipeline",
    label: "Residential pipeline",
    value: "--",
    note: "Will summarize active public-company residential projects.",
  },
  {
    id: "land",
    label: "Land reserves tracked",
    value: "--",
    note: "Backed by the `land_reserves` table from the initial schema.",
  },
  {
    id: "quality",
    label: "Location review coverage",
    value: "--",
    note: "Quality indicators will reflect exact vs city-level confidence.",
  },
];

export const adminKpis: KpiDefinition[] = [
  {
    id: "reports",
    label: "Pending reports",
    value: "0",
    note: "Upload and parsing are intentionally deferred to the next phase.",
  },
  {
    id: "review",
    label: "Projects awaiting review",
    value: "0",
    note: "Review queue hooks are scaffolded in the API and UI shell.",
  },
  {
    id: "publish",
    label: "Publish candidates",
    value: "0",
    note: "Public/admin separation is established before the workflow arrives.",
  },
];

export const placeholderProjectRows: PlaceholderProjectRow[] = [];

export const filterGroups = [
  { label: "City", value: "Not connected yet" },
  { label: "Neighborhood", value: "Not connected yet" },
  { label: "Company", value: "Not connected yet" },
  { label: "Project type", value: "Residential-only" },
  { label: "Permit status", value: "Planned API filter" },
  { label: "Report period", value: "Latest snapshot only" },
];
