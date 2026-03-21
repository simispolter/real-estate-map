import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { Panel } from "@/components/ui/panel";
import { adminKpis } from "@/lib/content";

export default function AdminPage() {
  return (
    <>
      <Panel
        eyebrow="Admin Dashboard"
        title="Internal review foundation"
        description="The admin route is separated at the app-layout level so authentication, review flows, and publish controls can evolve without leaking into the public UI."
      >
        <p className="panel-copy">
          Phase 1 keeps the dashboard structural only: no fake review data, but clear modules for the
          next implementation slices.
        </p>
      </Panel>

      <KpiGrid items={adminKpis} title="Admin work queues" />

      <section className="admin-grid">
        <Panel
          eyebrow="Reports"
          title="Reports queue"
          description="Upload, parse, and extraction preview endpoints are deferred to the next phase, but the dashboard slot and backend namespace already exist."
        >
          <p className="panel-copy">Next file to extend for this area: `apps/api/app/api/v1/endpoints/admin.py`.</p>
        </Panel>
        <Panel
          eyebrow="Review"
          title="Review queue"
          description="Project review, classification overrides, and merge tooling will attach here after ingestion creates canonical projects and conflicts."
        >
          <p className="panel-copy">
            Review-safe publication remains separate from raw extracted data. Live review surface:
            {" "}
            <a className="inline-link" href="/admin/projects">
              /admin/projects
            </a>
          </p>
        </Panel>
        <Panel
          eyebrow="Location"
          title="Location assignment"
          description="This module will consume `project_addresses` and `location_confidence` without introducing false-precision map pins."
        >
          <p className="panel-copy">Map interactions are intentionally postponed until Mapbox enters scope.</p>
        </Panel>
        <Panel
          eyebrow="Publish"
          title="Publish center"
          description="Public visibility will be controlled from this side of the system, preserving the admin-in-the-loop product rule from the docs."
        >
          <p className="panel-copy">Audit logging is already present in the initial SQL schema.</p>
        </Panel>
      </section>
    </>
  );
}
