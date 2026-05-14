"use client";

import { useState } from "react";

import { callApi, ClientApiError } from "@/lib/client-api";

export function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email) return;
    setBusy(true);
    setError(null);
    try {
      await callApi<null>("/v1/public/subscribers", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Could not subscribe.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <p className="text-sm text-fg-muted">
        You're subscribed. New posts will hit your inbox.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <label className="block text-xs font-medium text-fg-muted" htmlFor="sub-email">
        Email
      </label>
      <div className="flex gap-2">
        <input
          id="sub-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="flex-1 rounded-md border border-border bg-bg px-3 py-2 text-sm focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-fg disabled:opacity-60"
        >
          {busy ? "…" : "Subscribe"}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      )}
    </form>
  );
}
