import { useState } from "react";

import { Badge } from "@/components/shared/Badge/Badge";
import { Button } from "@/components/shared/Button/Button";
import { TextInput } from "@/components/shared/Field/Field";

import { formatCountries } from "../../countries";
import type { Stream } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";
import { ActionFeedback } from "../ActionFeedback/ActionFeedback";

// The geo stream: its countries (added / removed against the tracker marked) and an editor.
export function GeoEditor({
  stream,
  redirectHint,
  readOnly,
}: {
  stream: Stream;
  redirectHint: string;
  readOnly: boolean;
}) {
  const action = useCampaignAction();
  const [value, setValue] = useState(formatCountries(stream.draft_geo));
  const draft = stream.draft_geo ?? [];

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-medium">
        Geo stream <span className="font-normal text-muted-foreground">→ {redirectHint}</span>
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {draft.map((code) => (
          <Badge key={code} tone={stream.geo_added.includes(code) ? "info" : "neutral"}>
            {code}
            {stream.geo_added.includes(code) && " (added)"}
          </Badge>
        ))}
        {stream.geo_removed.map((code) => (
          <Badge key={code} tone="danger">
            <s>{code}</s>&nbsp;(removed)
          </Badge>
        ))}
      </div>
      {!readOnly && (
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            action.run("set-geo", { streamId: stream.id, countries: value });
          }}
        >
          <TextInput
            aria-label="Countries"
            placeholder="AU, NZ"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            className="max-w-xs"
          />
          <Button type="submit" disabled={action.busy || value === formatCountries(draft)}>
            Save countries
          </Button>
        </form>
      )}
      <ActionFeedback result={action.result} />
    </section>
  );
}
