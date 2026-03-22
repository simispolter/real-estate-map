import { redirect } from "next/navigation";

export default function LegacyAdminReportsPage() {
  redirect("/admin/sources");
}
