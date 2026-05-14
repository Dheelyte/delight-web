"use client";

import { useState } from "react";

import { callApi, ClientApiError } from "@/lib/client-api";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; email: string }
  | { kind: "error"; message: string };

export function UnsubscribeClient({ token }: { token: string }) {
  const [state, setState] = useState<State>({ kind: "idle" });

  async function confirm() {
    if (!token) {
      setState({ kind: "error", message: "Missing token." });
      return;
    }
    setState({ kind: "loading" });
    try {
      const sub = await callApi<{ email: string }>(
        "/v1/public/subscribers/unsubscribe",
        {
          method: "POST",
          body: JSON.stringify({ token }),
        },
      );
      setState({ kind: "ok", email: sub.email });
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof ClientApiError ? err.message : "Unsubscribe failed.",
      });
    }
  }

  if (state.kind === "ok") {
    return (
      <p className="mt-4 text-sm">
        Unsubscribed <strong>{state.email}</strong>. You can resubscribe anytime.
      </p>
    );
  }
  if (state.kind === "error") {
    return (
      <p role="alert" className="mt-4 text-sm text-red-600">
        {state.message}
      </p>
    );
  }
  return (
    <div className="mt-4 space-y-3">
      <p className="text-sm text-fg-muted">
        Click confirm to unsubscribe from the newsletter.
      </p>
      <button
        type="button"
        onClick={confirm}
        disabled={state.kind === "loading"}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg disabled:opacity-60"
      >
        {state.kind === "loading" ? "Unsubscribing…" : "Confirm unsubscribe"}
      </button>
    </div>
  );
}
