// The AdRobot API, as reached from the dashboard server (inside Docker: the `api` service).
// Only route loaders and actions call it; the browser never talks to the API directly.
const API_URL = process.env.API_URL ?? "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 30_000; // push and lookups wait on the tracker
const HEALTH_TIMEOUT_MS = 5_000;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  timeoutMs?: number;
};

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    throw new ApiError(0, "The API is unreachable");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response));
  }
  return (await response.json()) as T;
}

// The API answers {detail}: a message, or FastAPI's list of validation errors.
async function errorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail)) {
        return detail.map((item: { msg?: string }) => item.msg ?? "invalid").join("; ");
      }
    }
  } catch {
    // not JSON: fall through to the status line
  }
  return `${response.status} ${response.statusText}`;
}

export type Health = { healthy: boolean };

export async function getHealth(): Promise<Health> {
  try {
    await api("/health", { timeoutMs: HEALTH_TIMEOUT_MS });
    return { healthy: true };
  } catch {
    return { healthy: false };
  }
}
