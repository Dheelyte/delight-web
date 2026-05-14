/**
 * Same-origin proxy from /api/v1/* to the FastAPI backend.
 * Forwards cookies in *and* Set-Cookie out, so the browser only ever
 * speaks to the Next.js origin and session cookies stay first-party.
 */
import { cookies } from "next/headers";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(req: Request, segments: string[]): Promise<Response> {
  const url = new URL(req.url);
  const target = `${API_URL}/v1/${segments.join("/")}${url.search}`;
  const inboundCookies = await cookies();
  const session = inboundCookies.get("session")?.value;

  const headers = new Headers();
  for (const [k, v] of req.headers.entries()) {
    if (["host", "content-length", "cookie"].includes(k.toLowerCase())) continue;
    headers.set(k, v);
  }
  if (session) headers.set("cookie", `session=${session}`);

  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body: ["GET", "HEAD"].includes(req.method) ? undefined : await req.arrayBuffer(),
    redirect: "manual",
  });

  const responseHeaders = new Headers();
  for (const [k, v] of upstream.headers.entries()) {
    if (k.toLowerCase() === "content-encoding") continue;
    responseHeaders.append(k, v);
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: Request, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function POST(req: Request, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PUT(req: Request, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PATCH(req: Request, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function DELETE(req: Request, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
