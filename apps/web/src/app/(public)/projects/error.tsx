"use client";

import { Panel } from "@/components/ui/panel";

export default function ProjectsError({
  reset,
}: {
  reset: () => void;
}) {
  return (
    <Panel
      eyebrow="Error"
      title="Projects page failed to render"
      description="A rendering error occurred, but the route is now isolated behind a dedicated error boundary."
    >
      <div className="filter-actions">
        <button type="button" onClick={reset}>
          Retry
        </button>
      </div>
    </Panel>
  );
}
