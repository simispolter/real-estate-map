import { Panel } from "@/components/ui/panel";

export default function LoadingProjectsPage() {
  return (
    <div className="map-first-loading">
      <Panel
        eyebrow="Loading map-first discovery"
        title="Preparing the public map"
        description="Fetching filters, marker payloads, and the current side-panel cards."
      >
        <p className="panel-copy">
          The public route now opens into the map-first research experience, so this loading state mirrors the final layout instead of leaving a blank screen.
        </p>
      </Panel>
      <section className="map-first-loading-grid">
        <div className="map-loading-block" />
        <div className="map-loading-block map-loading-block-tall" />
      </section>
    </div>
  );
}
