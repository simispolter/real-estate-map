import { Panel } from "@/components/ui/panel";

export default function LoadingCompanyDetailPage() {
  return (
    <Panel
      eyebrow="Loading"
      title="Loading company detail"
      description="Fetching the latest report basis, KPI rollups, and linked projects."
    >
      <p className="panel-copy">The company route now shows a lightweight loading state while data resolves.</p>
    </Panel>
  );
}
