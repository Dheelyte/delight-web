/**
 * Public-API fetch helper for the reader-facing site.
 * No cookie forwarding - these endpoints are unauthenticated. Uses ISR-friendly
 * Next.js `revalidate` hints which RSCs honour for build-time + ISR.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class PublicApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function publicFetch<T>(
  path: string,
  { revalidate = 60 }: { revalidate?: number | false } = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: revalidate === false ? { revalidate: 0 } : { revalidate },
    headers: { accept: "application/json" },
  });
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const err = data as { error?: { code?: string; message?: string } } | null;
    throw new PublicApiError(
      res.status,
      err?.error?.code ?? "api_error",
      err?.error?.message ?? res.statusText,
    );
  }
  return data as T;
}
