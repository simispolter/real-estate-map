import { notFound } from "next/navigation";

import { AdminProjectEditor } from "@/components/admin/admin-project-editor";
import { Panel } from "@/components/ui/panel";
import { getAdminProjectDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function AdminProjectDetailPage({ params }: PageProps) {
  const { id } = await params;
  const result = await getAdminProjectDetail(id);

  if (result.state === "error" || !result.item) {
    notFound();
  }

  return (
    <>
      <Panel
        eyebrow="Admin Detail"
        title="Manual project correction"
        description="Use this page to inspect source-backed values, correct classification and location metadata, manage multiple addresses, and write internal notes with an audit trail."
      />
      <AdminProjectEditor project={result.item} />
    </>
  );
}
