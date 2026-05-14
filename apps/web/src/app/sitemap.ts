import type { MetadataRoute } from "next";

import { publicFetch } from "@/lib/public-api";
import { absoluteUrl } from "@/lib/site";
import type { SitemapOut } from "@/lib/types";

export const revalidate = 300;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { posts } = await publicFetch<SitemapOut>("/v1/public/sitemap", {
    revalidate: 300,
  });

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: absoluteUrl("/"), changeFrequency: "daily", priority: 1.0 },
    { url: absoluteUrl("/search"), changeFrequency: "yearly", priority: 0.2 },
    { url: absoluteUrl("/about"), changeFrequency: "yearly", priority: 0.5 },
    { url: absoluteUrl("/privacy"), changeFrequency: "yearly", priority: 0.1 },
    { url: absoluteUrl("/terms"), changeFrequency: "yearly", priority: 0.1 },
  ];

  const postRoutes: MetadataRoute.Sitemap = posts.map((p) => ({
    url: absoluteUrl(`/posts/${p.slug}`),
    lastModified: new Date(p.updated_at),
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  return [...staticRoutes, ...postRoutes];
}
