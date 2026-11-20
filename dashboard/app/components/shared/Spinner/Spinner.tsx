export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span
      role="status"
      aria-label={label}
      className="inline-block size-3.5 animate-spin rounded-full border-2 border-current border-r-transparent"
    />
  );
}
