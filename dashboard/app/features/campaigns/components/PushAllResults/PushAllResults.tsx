import type { PushItem } from "../../types";

// Push all: each campaign's outcome (a failure doesn't stop the others).
export function PushAllResults({ results }: { results: PushItem[] }) {
  if (results.length === 0) {
    return null;
  }
  return (
    <ul className="space-y-0.5 text-xs">
      {results.map((item) => (
        <li key={item.campaign_id} className={item.ok ? "text-emerald-300" : "text-red-300"}>
          {item.ok ? "✓" : "✗"} {item.name}
          {item.error && `: ${item.error}`}
          {item.mismatch.length > 0 && ` (the tracker stored something else: ${item.mismatch.join("; ")})`}
        </li>
      ))}
    </ul>
  );
}
