import { cn } from "@/lib/utils";

export function ApiStatus({ healthy }: { healthy: boolean }) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className={cn("size-2 rounded-full", healthy ? "bg-emerald-500" : "bg-destructive")} aria-hidden />
      {healthy ? "API OK" : "API unreachable"}
    </span>
  );
}
