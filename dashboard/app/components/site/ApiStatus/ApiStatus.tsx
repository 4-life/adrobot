import { cn } from "@/lib/utils";

export function ApiStatus({ healthy }: { healthy: boolean }) {
  return (
    <p className="flex items-center gap-2 text-sm text-muted-foreground">
      <span
        className={cn("size-2 rounded-full", healthy ? "bg-green-500" : "bg-destructive")}
        aria-hidden
      />
      {healthy ? "API OK" : "API unreachable"}
    </p>
  );
}
