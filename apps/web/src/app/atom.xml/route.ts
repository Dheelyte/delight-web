import { atomXml } from "@/lib/feed";
import { publicFetch } from "@/lib/public-api";
import type { PublicPostList } from "@/lib/types";

export const revalidate = 300;

export async function GET() {
  const { items } = await publicFetch<PublicPostList>(
    "/v1/public/posts?limit=50",
    { revalidate: 300 },
  );
  return new Response(atomXml(items), {
    headers: {
      "content-type": "application/atom+xml; charset=utf-8",
      "cache-control": "public, s-maxage=300, stale-while-revalidate=600",
    },
  });
}
