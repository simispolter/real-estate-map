import { redirect } from "next/navigation";

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ candidate?: string }>;
};

export default async function LegacyAdminReportDetailPage({ params, searchParams }: PageProps) {
  const [{ id }, { candidate }] = await Promise.all([params, searchParams]);
  redirect(candidate ? `/admin/sources/${id}?candidate=${candidate}` : `/admin/sources/${id}`);
}
