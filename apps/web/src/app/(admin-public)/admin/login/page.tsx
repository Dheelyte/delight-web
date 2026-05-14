import { LoginForm } from "./login-form";
import { safeNextPath } from "@/lib/safe-next";

export const metadata = { title: "Sign in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const next = safeNextPath(params.next);
  return (
    <main className="grid min-h-dvh place-items-center bg-bg px-6">
      <div className="w-full max-w-sm rounded-xl border border-border bg-bg-elevated p-8 shadow-sm">
        <h1 className="font-serif text-2xl">Sign in</h1>
        <p className="mt-1 text-sm text-fg-muted">Admin and editors only.</p>
        <LoginForm next={next} />
      </div>
    </main>
  );
}
