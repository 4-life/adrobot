// Country codes typed as "AU, NZ" or "au nz": the API normalizes and validates them.
export function parseCountries(value: string): string[] {
  return value
    .split(/[\s,;]+/)
    .map((code) => code.trim())
    .filter(Boolean);
}

export function formatCountries(codes: string[] | null): string {
  return (codes ?? []).join(", ");
}
