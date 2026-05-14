/**
 * Cloudinary delivery URL builder.
 *
 * The cloud name is preferentially read from the *response* (`MediaRef.cloud_name`
 * / `MediaOut.cloud_name`) so the browser never depends on a build-time env
 * var. The `NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME` env var is used only when no
 * explicit value is supplied — handy for pure-server callers (sitemaps,
 * OG image URLs at build time).
 *
 *   https://res.cloudinary.com/{cloud}/image/upload/{transforms}/{public_id}
 *
 * Transformations stay alphabetical. `f_auto` makes Cloudinary negotiate
 * AVIF / WebP / JPEG per request; `q_auto` picks quality per content.
 */

const ENV_CLOUD =
  process.env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME ??
  process.env.CLOUDINARY_CLOUD_NAME ??
  "";

const DEFAULT_WIDTHS = [400, 800, 1200, 1600] as const;

export type CloudinaryFit = "fill" | "limit";

export interface CloudinaryOptions {
  width?: number;
  height?: number;
  fit?: CloudinaryFit;
  focalX?: number | null;
  focalY?: number | null;
  dpr?: number;
  /** Override the cloud name on a per-call basis. Falls back to env. */
  cloudName?: string;
}

function _transforms(opts: CloudinaryOptions): string {
  const parts: string[] = ["f_auto", "q_auto"];
  if (opts.width) parts.push(`w_${Math.round(opts.width)}`);
  if (opts.height) parts.push(`h_${Math.round(opts.height)}`);
  if (opts.fit === "fill") {
    parts.push("c_fill");
    if (typeof opts.focalX === "number" && typeof opts.focalY === "number") {
      const x = clamp01(opts.focalX);
      const y = clamp01(opts.focalY);
      parts.push("g_xy_center", `x_${x.toFixed(3)}`, `y_${y.toFixed(3)}`);
    }
  } else if (opts.fit === "limit") {
    parts.push("c_limit");
  }
  if (opts.dpr && opts.dpr > 1) parts.push(`dpr_${opts.dpr}`);
  return parts.join(",");
}

function clamp01(v: number): number {
  if (!Number.isFinite(v)) return 0.5;
  if (v < 0) return 0;
  if (v > 1) return 1;
  return v;
}

function resolveCloud(opts: CloudinaryOptions): string {
  return opts.cloudName || ENV_CLOUD;
}

export function cloudinaryUrl(publicId: string, opts: CloudinaryOptions = {}): string {
  const cloud = resolveCloud(opts);
  if (!cloud) {
    // Loud signal: render a placeholder data URL rather than a 404'ing path,
    // and yell in dev so the developer notices the mis-config.
    if (typeof console !== "undefined") {
      // eslint-disable-next-line no-console
      console.warn(
        "cloudinaryUrl: no cloud name available — set NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME or pass cloudName explicitly.",
      );
    }
    return "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'/>";
  }
  return `https://res.cloudinary.com/${cloud}/image/upload/${_transforms(opts)}/${publicId}`;
}

export interface SrcSetResult {
  src: string;
  srcSet: string;
  sizes: string;
}

export function cloudinarySrcSet(
  publicId: string,
  opts: Omit<CloudinaryOptions, "width"> & {
    widths?: readonly number[];
    sizes?: string;
  } = {},
): SrcSetResult {
  const widths = opts.widths ?? DEFAULT_WIDTHS;
  const sizes = opts.sizes ?? "(min-width: 1024px) 800px, 100vw";
  const srcSet = widths
    .map((w) => `${cloudinaryUrl(publicId, { ...opts, width: w })} ${w}w`)
    .join(", ");
  const fallbackWidth = widths[Math.floor(widths.length / 2)] ?? widths[0]!;
  const src = cloudinaryUrl(publicId, { ...opts, width: fallbackWidth });
  return { src, srcSet, sizes };
}
