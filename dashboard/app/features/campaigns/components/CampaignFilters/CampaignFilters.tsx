import { Button } from "@/components/shared/Button/Button";
import { Select, TextInput } from "@/components/shared/Field/Field";

import type { CampaignFilter, FilterOptions, Scope } from "../../filters";
import type { LookupItem } from "../../types";

function IdSelect({
  label,
  items,
  value,
  onChange,
}: {
  label: string;
  items: LookupItem[];
  value: number | null;
  onChange: (value: number | null) => void;
}) {
  return (
    <Select
      aria-label={label}
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
      className="w-auto"
    >
      <option value="">All {label.toLowerCase()}s</option>
      {items.map((item) => (
        <option key={item.id} value={item.id}>
          {item.name}
        </option>
      ))}
    </Select>
  );
}

const SCOPES: [Scope, string][] = [
  ["ours", "Ours"],
  ["all", "All"],
];

export function CampaignFilters({
  filter,
  options,
  onChange,
}: {
  filter: CampaignFilter;
  options: FilterOptions;
  onChange: (filter: CampaignFilter) => void;
}) {
  const set = (patch: Partial<CampaignFilter>) => onChange({ ...filter, ...patch });

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="group" aria-label="Show" className="flex rounded-md border p-0.5">
        {SCOPES.map(([scope, label]) => (
          <Button
            key={scope}
            size="sm"
            variant={filter.scope === scope ? "secondary" : "ghost"}
            aria-pressed={filter.scope === scope}
            onClick={() => set({ scope })}
          >
            {label}
          </Button>
        ))}
      </div>
      <TextInput
        aria-label="Search campaigns"
        placeholder="Search name or alias"
        value={filter.search}
        onChange={(event) => set({ search: event.target.value })}
        className="w-56"
      />
      <IdSelect label="Group" items={options.groups} value={filter.groupId} onChange={(groupId) => set({ groupId })} />
      <IdSelect label="Domain" items={options.domains} value={filter.domainId} onChange={(domainId) => set({ domainId })} />
      <IdSelect label="Source" items={options.sources} value={filter.sourceId} onChange={(sourceId) => set({ sourceId })} />
      <label className="flex items-center gap-1.5 text-sm">
        <input
          type="checkbox"
          checked={filter.pendingOnly}
          onChange={(event) => set({ pendingOnly: event.target.checked })}
        />
        Pending only
      </label>
    </div>
  );
}
