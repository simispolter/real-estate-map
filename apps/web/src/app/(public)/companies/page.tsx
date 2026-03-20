import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { Panel } from "@/components/ui/panel";
import { companyKpis } from "@/lib/content";

export default function CompaniesPage() {
  return (
    <>
      <Panel
        eyebrow="Companies"
        title="Public company coverage"
        description="The company route is ready for the future public company API and keeps company-level pipeline analysis separate from project-level browsing."
      >
        <p className="panel-copy">
          The final implementation will read from the versioned company list and company detail endpoints
          once published company summaries are available.
        </p>
      </Panel>

      <KpiGrid items={companyKpis} title="Company summary scaffold" />

      <section className="company-grid">
        <Panel
          eyebrow="Upcoming"
          title="Company list surface"
          description="Reserved for a sortable table with company metadata, coverage state, and roll-up KPIs."
        >
          <div className="callout-list">
            <div className="callout-item">Ticker, status, and project counts</div>
            <div className="callout-item">Land reserve roll-up</div>
            <div className="callout-item">Public-company residential pipeline summary</div>
          </div>
        </Panel>
        <Panel
          eyebrow="Land Reserves"
          title="Future reserve visibility"
          description="Land reserves are modeled separately from active projects so planning inventory is not confused with marketed residential projects."
        >
          <p className="panel-copy">
            The schema and API structure are ready for this block, but no sample operational data is
            injected in Phase 1.
          </p>
        </Panel>
      </section>
    </>
  );
}
