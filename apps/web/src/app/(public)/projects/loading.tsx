import { Panel } from "@/components/ui/panel";

export default function LoadingProjectsPage() {
  return (
    <div className="map-first-loading">
      <Panel
        eyebrow="Loading database view"
        title="Preparing the project database"
        description="Fetching project filters, counts, and the current canonical project table."
      >
        <p className="panel-copy">
          This phase prioritizes a clear ingestion-to-database workflow, so the public loading state mirrors the filter and table layout instead of a blank screen.
        </p>
      </Panel>
      <section className="map-first-loading-grid">
        <div className="map-loading-block" />
        <div className="map-loading-block map-loading-block-tall" />
      </section>
    </div>
  );
}
