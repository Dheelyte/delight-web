import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        "bg-elevated": "var(--color-bg-elevated)",
        "bg-muted": "var(--color-bg-muted)",
        fg: "var(--color-fg)",
        "fg-muted": "var(--color-fg-muted)",
        "fg-subtle": "var(--color-fg-subtle)",
        border: "var(--color-border)",
        "border-strong": "var(--color-border-strong)",
        accent: "var(--color-accent)",
        "accent-fg": "var(--color-accent-fg)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
      },
      maxWidth: {
        prose: "65ch",
      },
    },
  },
  plugins: [],
};

export default config;
