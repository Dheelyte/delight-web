/**
 * Server-side fetch helper for talking to the FastAPI backend.
 * Forwards the session cookie from the incoming request when on the server.
 */
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<{ data: T; response: Response }> {
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  const headers = new Headers(init.headers);
  if (session) {
    headers.set("cookie", `session=${session}`);
  }
  if (init.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const text = await response.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!response.ok) {
    const err = data as { error?: { code?: string; message?: string } } | null;
    throw new ApiError(
      response.status,
      err?.error?.code ?? "api_error",
      err?.error?.message ?? response.statusText,
    );
  }

  return { data: data as T, response };
}
