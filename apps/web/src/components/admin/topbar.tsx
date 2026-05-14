"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { callApi } from "@/lib/client-api";
import type { Me } from "@/lib/types";

export function Topbar({ me }: { me: Me }) {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setSigningOut(true);
    try {
      await callApi<null>("/v1/auth/logout", { method: "POST" });
    } finally {
      router.replace("/admin/login");
    }
  }

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-3 text-sm">
      <div className="text-fg-muted">
        Signed in as <span className="text-fg">{me.email}</span>{" "}
        <span className="text-fg-subtle">({me.role})</span>
      </div>
      <button
        type="button"
        onClick={signOut}
        disabled={signingOut}
        className="rounded-md border border-border px-3 py-1 text-fg-muted hover:bg-bg-muted disabled:opacity-60"
      >
        {signingOut ? "Signing out…" : "Sign out"}
      </button>
    </header>
  );
}
