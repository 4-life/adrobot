import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type BadgeTone = "neutral" | "info" | "warning" | "danger" | "success";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-muted text-muted-foreground",
  info: "bg-sky-500/15 text-sky-300",
  warning: "bg-amber-500/15 text-amber-300",
  danger: "bg-red-500/15 text-red-300",
  success: "bg-emerald-500/15 text-emerald-300",
};

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={cn("inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium", TONES[tone])}
    >
      {children}
    </span>
  );
}
