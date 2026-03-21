import { notFound } from "next/navigation";

import { AdminReportWorkspace } from "@/components/admin/admin-report-workspace";
import { Panel } from "@/components/ui/panel";
import { getAdminReportDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ candidate?: string }>;
};

export default async function AdminReportDetailPage({ params, searchParams }: PageProps) {
  const [{ id }, { candidate }] = await Promise.all([params, searchParams]);
  const result = await getAdminReportDetail(id);

  if (result.state === "error" || !result.item) {
    notFound();
  }

  return (
    <>
      <Panel
        eyebrow="Admin Detail"
        title="Report staging and publish workspace"
        description="This is the manual bridge between a source report and canonical project data. Keep source-backed staging separate, review the comparison, then publish approved values with provenance."
      />
      <AdminReportWorkspace initialCandidateId={candidate ?? null} initialReport={result.item} />
    </>
  );
}
