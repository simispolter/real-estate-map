import { Panel } from "@/components/ui/panel";

export default function LoadingProjectsPage() {
  return (
    <Panel
      eyebrow="Loading"
      title="Loading projects"
      description="Fetching project rows and filter metadata."
    >
      <p className="panel-copy">The route now has a lightweight loading state instead of a blank or broken screen.</p>
    </Panel>
  );
}
