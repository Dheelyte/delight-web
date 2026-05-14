"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";

interface Props {
  url: string;
  title: string;
  className?: string;
}

/**
 * Post share controls: native share (mobile), copy-link, and the main social
 * platforms. The social entries are plain `<a target="_blank">` links — no
 * SDKs, no tracking pixels, nothing that needs a CSP exception.
 */
export function ShareBar({ url, title, className }: Props) {
  const [copied, setCopied] = useState(false);
  const [canNativeShare, setCanNativeShare] = useState(false);

  useEffect(() => {
    setCanNativeShare(
      typeof navigator !== "undefined" && typeof navigator.share === "function",
    );
  }, []);

  const encodedUrl = encodeURIComponent(url);
  const encodedTitle = encodeURIComponent(title);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked (insecure context / permissions) — fail silently;
      // the social links still work.
    }
  }

  async function nativeShare() {
    try {
      await navigator.share({ title, url });
    } catch {
      // User dismissed the share sheet — nothing to do.
    }
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 border-t border-border pt-6",
        className,
      )}
    >
      <span className="mr-1 text-xs font-semibold uppercase tracking-wider text-fg-subtle">
        Share
      </span>

      {canNativeShare && (
        <button
          type="button"
          onClick={nativeShare}
          className={iconBtn}
          aria-label="Share this post"
          title="Share"
        >
          <ShareIcon />
        </button>
      )}

      <a
        href={`https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`}
        target="_blank"
        rel="noopener noreferrer"
        className={iconBtn}
        aria-label="Share on X"
        title="Share on X"
      >
        <XIcon />
      </a>
      <a
        href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        className={iconBtn}
        aria-label="Share on LinkedIn"
        title="Share on LinkedIn"
      >
        <LinkedInIcon />
      </a>
      <a
        href={`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        className={iconBtn}
        aria-label="Share on Facebook"
        title="Share on Facebook"
      >
        <FacebookIcon />
      </a>

      <button
        type="button"
        onClick={copyLink}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-fg-muted transition-colors hover:bg-bg-muted hover:text-fg"
        aria-live="polite"
      >
        {copied ? <CheckIcon /> : <LinkIcon />}
        {copied ? "Copied" : "Copy link"}
      </button>
    </div>
  );
}

const iconBtn =
  "grid h-8 w-8 place-items-center rounded-md border border-border text-fg-muted transition-colors hover:bg-bg-muted hover:text-fg";

const svgProps = {
  xmlns: "http://www.w3.org/2000/svg",
  width: 15,
  height: 15,
  viewBox: "0 0 24 24",
  "aria-hidden": true,
};

const strokeProps = {
  ...svgProps,
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function ShareIcon() {
  return (
    <svg {...strokeProps}>
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg {...strokeProps}>
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg {...strokeProps}>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg {...svgProps} fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg {...svgProps} fill="currentColor">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg {...svgProps} fill="currentColor">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}
