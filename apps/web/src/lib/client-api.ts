/** Client-side API helper. Uses the same-origin proxy so cookies just work. */

export class ClientApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function callApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  const res = await fetch(`/api${path}`, { ...init, headers });
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const err = data as { error?: { code?: string; message?: string } } | null;
    throw new ClientApiError(
      res.status,
      err?.error?.code ?? "api_error",
      err?.error?.message ?? res.statusText,
    );
  }
  return data as T;
}
