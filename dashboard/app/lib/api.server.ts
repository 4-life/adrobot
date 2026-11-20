// The AdRobot API, as reached from the dashboard server (inside Docker: the `api` service).
const API_URL = process.env.API_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 5000;

export type Health = { healthy: boolean };

export async function getHealth(): Promise<Health> {
  try {
    const response = await fetch(`${API_URL}/health`, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    return { healthy: response.ok };
  } catch {
    return { healthy: false };
  }
}
