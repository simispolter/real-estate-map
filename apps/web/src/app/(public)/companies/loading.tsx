import { Panel } from "@/components/ui/panel";

export default function LoadingCompaniesPage() {
  return (
    <Panel
      eyebrow="Loading"
      title="Loading companies"
      description="Fetching company coverage data from the API."
    >
      <p className="panel-copy">The companies route now has a lightweight loading state while data resolves.</p>
    </Panel>
  );
}
