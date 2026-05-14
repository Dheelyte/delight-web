import { SeriesManager } from "@/components/admin/series-manager";
import { apiFetch } from "@/lib/api";

interface Series {
  id: string;
  slug: string;
  title: string;
  description: string | null;
}

export const dynamic = "force-dynamic";

export default async function SeriesPage() {
  const { data } = await apiFetch<Series[]>("/v1/series");
  return (
    <div className="space-y-4">
      <h1 className="font-serif text-3xl">Series</h1>
      <SeriesManager initial={data} />
    </div>
  );
}
