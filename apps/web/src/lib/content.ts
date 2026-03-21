import type { KpiDefinition } from "@real-estat-map/shared";

export const publicNavigation = [
  { href: "/", label: "Overview" },
  { href: "/projects", label: "Projects" },
  { href: "/companies", label: "Companies" },
  { href: "/admin", label: "Admin" },
];

export const adminNavigation = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/reports", label: "Reports" },
  { href: "/admin/projects", label: "Projects Review" },
  { href: "/admin#reports", label: "Reports Queue" },
  { href: "/admin#publish", label: "Publish Center" },
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
