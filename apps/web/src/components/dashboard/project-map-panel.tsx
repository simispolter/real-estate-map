import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";

export function ProjectMapPanel() {
  return (
    <Panel
      eyebrow="Map Surface"
      title="Project map panel"
      description="Phase 1 keeps the map contract and page structure in place without introducing Mapbox or false precision."
      actions={<Tag tone="warning">Mapbox deferred</Tag>}
    >
      <div className="map-placeholder">
        <div className="map-grid" aria-hidden="true" />
        <div className="map-callout">
          <h3>Location confidence will drive the visual language</h3>
          <p className="panel-copy">
            Exact, street, neighborhood, city, and unknown badges are reserved in the schema and UI
            from the start.
          </p>
        </div>
      </div>
    </Panel>
  );
}
