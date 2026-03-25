import type { KpiDefinition } from "@real-estat-map/shared";

export const publicNavigation = [
  { href: "/projects", label: "Projects" },
  { href: "/companies", label: "Companies" },
  { href: "/admin", label: "Admin" },
];

export const adminNavigation = [
  { href: "/admin/projects", label: "Projects" },
  { href: "/admin/intake", label: "Intake" },
  { href: "/admin/sources", label: "Sources" },
  { href: "/admin/coverage/companies", label: "Coverage" },
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
    id: "projects",
    label: "Canonical projects",
    value: "0",
    note: "Admin now centers on canonical projects, not raw source files.",
  },
  {
    id: "intake",
    label: "Intake candidates",
    value: "0",
    note: "Candidate review stays separate from canonical edits and publishing.",
  },
  {
    id: "sources",
    label: "Tracked sources",
    value: "0",
    note: "Reports remain supporting source records behind the project workflow.",
  },
];
