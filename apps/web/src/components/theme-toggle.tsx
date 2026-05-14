"use client";

import { useEffect, useState } from "react";

import type { Theme } from "@/lib/theme";
import { DEFAULT_THEME } from "@/lib/theme";

const COOKIE = "theme";

function setCookie(v: Theme) {
  document.cookie = `${COOKIE}=${v}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
}

function applyTheme(v: Theme) {
  document.documentElement.setAttribute("data-theme", v);
}

const LABEL: Record<Theme, string> = {
  light: "Light",
  dark: "Dark",
};

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(DEFAULT_THEME);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const match = document.cookie.match(/(?:^|;\s*)theme=(light|dark)/);
    if (match?.[1] === "dark" || match?.[1] === "light") {
      setTheme(match[1]);
    }
    setMounted(true);
  }, []);

  function toggle() {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    setCookie(next);
    applyTheme(next);
  }

  const next: Theme = theme === "light" ? "dark" : "light";
  const label = `Switch to ${LABEL[next].toLowerCase()} theme`;

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className="grid h-8 w-8 place-items-center rounded-md border border-border text-fg-muted transition-colors hover:bg-bg-muted hover:text-fg"
    >
      {/* Pre-mount spacer keeps SSR and first client render identical. */}
      {mounted ? (
        theme === "light" ? <SunIcon /> : <MoonIcon />
      ) : (
        <span className="h-4 w-4" />
      )}
    </button>
  );
}

const svgProps = {
  xmlns: "http://www.w3.org/2000/svg",
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

function SunIcon() {
  return (
    <svg {...svgProps}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg {...svgProps}>
      <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z" />
    </svg>
  );
}
