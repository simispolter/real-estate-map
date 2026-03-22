import { notFound } from "next/navigation";

import { AdminReportWorkspace } from "@/components/admin/admin-report-workspace";
import { Panel } from "@/components/ui/panel";
import { getAdminCandidateDetail, getAdminReportDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ candidateId: string }>;
};

export default async function AdminIntakeDetailPage({ params }: PageProps) {
  const { candidateId } = await params;
  const candidate = await getAdminCandidateDetail(candidateId);

  if (candidate.state === "error" || !candidate.item) {
    notFound();
  }

  const report = await getAdminReportDetail(candidate.item.reportId);
  if (report.state === "error" || !report.item) {
    notFound();
  }

  return (
    <>
      <Panel
        eyebrow="Admin Intake"
        title="Candidate review workspace"
        description="Review the candidate against canonical project data, make the match decision, and publish into the project/snapshot history when ready."
      />
      <AdminReportWorkspace initialCandidateId={candidateId} initialReport={report.item} />
    </>
  );
}
