import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";

type FilterItem = {
  label: string;
  value: string;
};

export function FiltersPanel({
  description,
  items,
  title = "Filters",
}: {
  description: string;
  items: FilterItem[];
  title?: string;
}) {
  return (
    <Panel
      eyebrow="Search Surface"
      title={title}
      description={description}
      actions={<Tag tone="accent">URL-driven state next</Tag>}
    >
      <div className="filter-grid">
        {items.map((item) => (
          <div key={item.label} className="filter-item">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
    </Panel>
  );
}
