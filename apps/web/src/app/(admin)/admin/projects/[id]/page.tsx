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
        eyebrow="ניהול פרויקט"
        title="עריכת פרויקט קנוני"
        description="ערכו את פרטי הליבה של הפרויקט, נהלו מיקום וכתובות, ובדקו מקורות, מועמדים והיסטוריית snapshot ממקום אחד."
      />
      <AdminProjectEditor companies={companiesResult.items} project={result.item} />
    </>
  );
}
