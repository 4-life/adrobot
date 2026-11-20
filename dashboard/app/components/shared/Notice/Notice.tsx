import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Tone = "info" | "error" | "warning";

const TONES: Record<Tone, string> = {
  info: "border-sky-500/30 bg-sky-500/10 text-sky-200",
  error: "border-red-500/30 bg-red-500/10 text-red-200",
  warning: "border-amber-500/30 bg-amber-500/10 text-amber-200",
};

export function Notice({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={cn("rounded-md border px-3 py-2 text-sm", TONES[tone])}>
      {children}
    </div>
  );
}
