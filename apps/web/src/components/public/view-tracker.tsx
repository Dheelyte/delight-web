"use client";

import { useEffect } from "react";

import { callApi } from "@/lib/client-api";

/**
 * Fires once per mount. The backend dedupes server-side per (session, post)
 * within a one-hour window, so brief re-renders or navigations are safe.
 */
export function ViewTracker({ postSlug }: { postSlug: string }) {
  useEffect(() => {
    const ref = typeof document !== "undefined" ? document.referrer : "";
    void callApi("/v1/public/views", {
      method: "POST",
      body: JSON.stringify({ post_slug: postSlug, referrer: ref || null }),
    }).catch(() => {
      // Telemetry must never break the page.
    });
  }, [postSlug]);
  return null;
}
