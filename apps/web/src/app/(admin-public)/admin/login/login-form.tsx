"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { cn } from "@/lib/cn";

export function LoginForm({ next }: { next: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as {
          error?: { message?: string };
        } | null;
        setError(data?.error?.message ?? "Sign-in failed.");
        return;
      }
      router.replace(next);
    } finally {
      setPending(false);
    }
  }

  const inputCls =
    "mt-1 w-full rounded-md border border-border bg-bg px-3 py-2 text-sm " +
    "focus:border-accent focus:outline-none";
  const labelCls = "block text-xs font-medium text-fg-muted";

  return (
    <form onSubmit={onSubmit} className="mt-6 space-y-4">
      <div>
        <label htmlFor="email" className={labelCls}>
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputCls}
        />
      </div>
      <div>
        <label htmlFor="password" className={labelCls}>
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={inputCls}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className={cn(
          "w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg",
          "transition-opacity disabled:opacity-60",
        )}
      >
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
