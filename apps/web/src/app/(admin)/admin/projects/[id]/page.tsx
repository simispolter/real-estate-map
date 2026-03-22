import { notFound } from "next/navigation";

import { AdminProjectEditor } from "@/components/admin/admin-project-editor";
import { Panel } from "@/components/ui/panel";
import { getAdminProjectDetail, getCompanies } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function AdminProjectDetailPage({ params }: PageProps) {
  const { id } = await params;
  const [result, companiesResult] = await Promise.all([getAdminProjectDetail(id), getCompanies()]);

  if (result.state === "error" || !result.item) {
    notFound();
  }

  return (
    <>
      <Panel
        eyebrow="Admin Detail"
        title="Canonical project management"
        description="Edit core project fields directly, manage aliases and addresses, review linked candidates and sources, and create or update snapshots without centering the workflow around reports."
      />
      <AdminProjectEditor companies={companiesResult.items} project={result.item} />
    </>
  );
}
