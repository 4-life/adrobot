import { useFetcher } from "react-router";

import type { ActionResult } from "./types";

type FieldValue = string | number | boolean | null | (string | number)[];

// Posts one campaign action (an `intent` and its fields) to the home route's action, without
// navigating; each component gets its own pending state and result.
export function useCampaignAction() {
  const fetcher = useFetcher<ActionResult>();

  const run = (intent: string, fields: Record<string, FieldValue> = {}) => {
    const form = new FormData();
    form.set("intent", intent);
    for (const [name, value] of Object.entries(fields)) {
      if (value === null) {
        continue;
      }
      if (Array.isArray(value)) {
        for (const item of value) {
          form.append(name, String(item));
        }
      } else {
        form.set(name, String(value));
      }
    }
    void fetcher.submit(form, { method: "post", action: "/?index" });
  };

  const result = fetcher.data;
  return {
    run,
    busy: fetcher.state !== "idle",
    result,
    error: result && !result.ok ? result.error : null,
  };
}
