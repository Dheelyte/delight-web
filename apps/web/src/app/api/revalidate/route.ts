/**
 * On-demand ISR revalidation receiver.
 *
 * The API calls this after a post is published / updated / deleted so the
 * cache invalidates within a second instead of waiting for `revalidate: 300`.
 *
 *   POST /api/revalidate
 *   Header: x-revalidate-secret: <REVALIDATE_SECRET>
 *   Body:   { "paths": ["/", "/posts/foo", "/tags/x"], "tags": ["posts"] }
 */
import { revalidatePath, revalidateTag } from "next/cache";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SECRET = process.env.REVALIDATE_SECRET ?? "";

export async function POST(req: Request) {
  if (!SECRET) {
    return Response.json(
      { error: { code: "not_configured", message: "REVALIDATE_SECRET not set." } },
      { status: 503 },
    );
  }
  if (req.headers.get("x-revalidate-secret") !== SECRET) {
    return Response.json(
      { error: { code: "forbidden", message: "Bad secret." } },
      { status: 403 },
    );
  }

  const body = (await req.json().catch(() => null)) as
    | { paths?: string[]; tags?: string[] }
    | null;
  if (!body) {
    return Response.json(
      { error: { code: "bad_request", message: "Invalid JSON." } },
      { status: 400 },
    );
  }

  const revalidatedPaths: string[] = [];
  for (const p of body.paths ?? []) {
    if (typeof p === "string" && p.startsWith("/")) {
      revalidatePath(p);
      revalidatedPaths.push(p);
    }
  }
  const revalidatedTags: string[] = [];
  for (const t of body.tags ?? []) {
    if (typeof t === "string" && t.length > 0 && t.length <= 80) {
      revalidateTag(t);
      revalidatedTags.push(t);
    }
  }

  return Response.json({ revalidatedPaths, revalidatedTags });
}
