import { useEffect } from "react";
import { useFetcher } from "react-router";

import { useToast } from "@/components/shared/Toast/Toaster";

import { resultToasts } from "./components/ResultToast/ResultToast";
import type { ActionResult } from "./types";

export const CAMPAIGN_ACTION_ROUTE = "/campaign-action"; // routes/campaign-action.ts

type FieldValue = string | number | boolean | null | (string | number)[];

// Posts one campaign action (an `intent` and its fields) to the campaign-action route, without
// navigating (every page's loader then reloads); each component gets its own pending state.
// The result is shown as toasts, unless `toasts: false` (inside a modal dialog, where a toast
// would be hidden behind it: show `error` there instead).
export function useCampaignAction({ toasts = true }: { toasts?: boolean } = {}) {
  const fetcher = useFetcher<ActionResult>();
  const toast = useToast();
  const result = fetcher.data;

  // Once per result: fetcher.data is a new object after every submission.
  useEffect(() => {
    if (toasts && result) {
      for (const { tone, content } of resultToasts(result)) {
        toast(tone, content);
      }
    }
  }, [result, toasts, toast]);

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
    void fetcher.submit(form, { method: "post", action: CAMPAIGN_ACTION_ROUTE });
  };

  return {
    run,
    busy: fetcher.state !== "idle",
    result,
    error: result && !result.ok ? result.error : null,
  };
}
