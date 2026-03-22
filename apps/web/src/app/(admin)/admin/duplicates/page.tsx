import { AdminDuplicatesDashboard } from "@/components/admin/admin-duplicates-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminDuplicates } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminDuplicatesPage() {
  const { items, state } = await getAdminDuplicates();

  return (
    <>
      <Panel
        eyebrow="Admin Duplicates"
        title="Canonical duplicate review"
        description="Review likely duplicate canonical projects, inspect matching signals, and merge carefully without losing aliases, addresses, snapshots, provenance, or audit history."
      />

      {state === "error" ? (
        <Panel eyebrow="Status" title="Duplicate suggestions are temporarily unavailable">
          <p className="panel-copy">The duplicate detection route is live, but the current suggestions could not be loaded.</p>
        </Panel>
      ) : null}

      <AdminDuplicatesDashboard initialItems={items} />
    </>
  );
}
