import { notFound } from "next/navigation";

import { AdminLayerEditor } from "@/components/admin/admin-layer-editor";
import { Panel } from "@/components/ui/panel";
import { getAdminLayerDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function AdminLayerDetailPage({ params }: PageProps) {
  const { id } = await params;
  const result = await getAdminLayerDetail(id);

  if (result.state === "error" || !result.item) {
    notFound();
  }

  return (
    <>
      <Panel
        eyebrow="Admin Layer Detail"
        title={result.item.layerName}
        description="Registry metadata, sample records, and relation-prep visibility for one external layer."
      />
      <AdminLayerEditor layer={result.item} />
    </>
  );
}
