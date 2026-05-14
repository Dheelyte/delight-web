import { UnsubscribeClient } from "./unsubscribe-client";

export const dynamic = "force-dynamic";
export const metadata = { title: "Unsubscribe", robots: "noindex, nofollow" };

export default async function UnsubscribePage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token = "" } = await searchParams;
  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-16">
      <div className="max-w-md">
        <h1 className="font-serif text-3xl">Unsubscribe</h1>
        <UnsubscribeClient token={token} />
      </div>
    </main>
  );
}
