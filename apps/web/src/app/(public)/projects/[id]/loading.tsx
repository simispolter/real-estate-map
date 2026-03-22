import { Panel } from "@/components/ui/panel";

export default function LoadingProjectDetailPage() {
  return (
    <Panel
      eyebrow="Loading"
      title="Loading project detail"
      description="Fetching the latest project snapshot, provenance, and history."
    >
      <p className="panel-copy">The detail route stays responsive while the research view resolves.</p>
    </Panel>
  );
}
