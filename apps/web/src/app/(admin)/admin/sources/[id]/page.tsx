import { notFound } from "next/navigation";

import { AdminReportWorkspace } from "@/components/admin/admin-report-workspace";
import { Panel } from "@/components/ui/panel";
import { getAdminReportDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ candidate?: string }>;
};

export default async function AdminSourceDetailPage({ params, searchParams }: PageProps) {
  const [{ id }, { candidate }] = await Promise.all([params, searchParams]);
  const result = await getAdminReportDetail(id);

  if (result.state === "error" || !result.item) {
    notFound();
  }

  return (
    <>
      <Panel
        eyebrow="Admin Sources"
        title="Source staging workspace"
        description="Keep the report workflow practical: update the source record, extract project rows into staging, review candidates, and publish snapshots into canonical projects."
      />
      <AdminReportWorkspace initialCandidateId={candidate ?? null} initialReport={result.item} />
    </>
  );
}
