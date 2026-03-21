import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";

type FilterField = {
  label: string;
  name: string;
  value?: string;
  type?: "select" | "text";
  placeholder?: string;
  options?: Array<{
    label: string;
    value: string;
  }>;
};

export function FiltersPanel({
  action,
  description,
  fields,
  resetHref = "/projects",
  title = "Filters",
}: {
  action?: string;
  description: string;
  fields?: FilterField[] | null;
  resetHref?: string;
  title?: string;
}) {
  const safeFields = Array.isArray(fields) ? fields : [];
  const hasActiveFilters = safeFields.some((field) => field?.value);

  return (
    <Panel
      eyebrow="Search Surface"
      title={title}
      description={description}
      actions={<Tag tone="accent">URL-driven filters</Tag>}
    >
      {safeFields.length > 0 ? (
        <form action={action} className="filter-form" method="GET">
          <div className="filter-grid">
            {safeFields.map((field) => {
              const safeOptions = Array.isArray(field.options) ? field.options : [];
              const fieldType = field.type ?? "select";

              return (
                <label key={field.name} className="filter-item filter-field">
                  <span>{field.label}</span>
                  {fieldType === "text" ? (
                    <input
                      defaultValue={field.value ?? ""}
                      name={field.name}
                      placeholder={field.placeholder ?? `Search ${field.label.toLowerCase()}`}
                      type="text"
                    />
                  ) : (
                    <select name={field.name} defaultValue={field.value ?? ""}>
                      <option value="">All</option>
                      {safeOptions.map((option) => (
                        <option key={`${field.name}-${option.value}`} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  )}
                </label>
              );
            })}
          </div>
          <div className="filter-actions">
            <button type="submit">Apply filters</button>
            {hasActiveFilters ? (
              <a href={resetHref} className="filter-reset">
                Reset
              </a>
            ) : null}
          </div>
        </form>
      ) : (
        <div className="empty-state">
          <strong>Filters are temporarily unavailable.</strong>
          <p className="panel-copy">
            The page can still render, but filter metadata did not load so the controls were hidden.
          </p>
        </div>
      )}
    </Panel>
  );
}
