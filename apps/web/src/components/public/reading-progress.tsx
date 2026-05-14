"use client";

import { useEffect, useState } from "react";

/**
 * Thin fixed bar at the top of the viewport showing scroll progress *through
 * the article* - it hits 100% at the end of the post body, not the end of the
 * page (so comments/footer don't dilute it).
 *
 * Decorative, so `aria-hidden`. Targets an element by id (default
 * `post-article`); does nothing if that element isn't on the page.
 */
export function ReadingProgress({
  targetId = "post-article",
}: {
  targetId?: string;
}) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const el = document.getElementById(targetId);
    if (!el) return;

    function update() {
      // `el` is non-null here - guarded above, and the effect re-runs per id.
      const target = el as HTMLElement;
      const scrollable = target.offsetHeight - window.innerHeight;
      if (scrollable <= 0) {
        setProgress(0);
        return;
      }
      const scrolled = -target.getBoundingClientRect().top;
      setProgress(Math.min(1, Math.max(0, scrolled / scrollable)));
    }

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [targetId]);

  return (
    <div
      aria-hidden="true"
      className="fixed inset-x-0 top-0 z-50 h-1"
    >
      <div
        className="h-full bg-accent transition-[width] duration-75 ease-out"
        style={{ width: `${(progress * 100).toFixed(2)}%` }}
      />
    </div>
  );
}
