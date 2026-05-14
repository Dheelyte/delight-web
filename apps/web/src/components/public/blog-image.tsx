/**
 * Responsive image for blog content. Alt is required by the type - TypeScript
 * itself is the lint rule. We render a wrapper + a dedicated blurred placeholder
 * layer so the 24-px LQIP looks like real-world blur instead of pixel art when
 * upscaled to full width.
 *
 * Uses native <img> with srcset rather than next/image because Cloudinary already
 * handles AVIF/WebP negotiation server-side via `f_auto`, and the loader plus
 * its image-optimisation pass would be wasted bytes.
 */
import { cn } from "@/lib/cn";
import {
  cloudinarySrcSet,
  cloudinaryUrl,
  type CloudinaryOptions,
} from "@/lib/cloudinary";

interface Props {
  publicId: string;
  alt: string;
  width: number;
  height: number;
  focalX?: number | null;
  focalY?: number | null;
  placeholder?: string | null; // data: URL (LQIP)
  className?: string;
  sizes?: string;
  /** When set, request a fixed-aspect crop via `c_fill`. */
  fit?: CloudinaryOptions["fit"];
  priority?: boolean;
  /** Cloud name from the API response; falls back to env. */
  cloudName?: string;
}

export function BlogImage({
  publicId,
  alt,
  width,
  height,
  focalX = null,
  focalY = null,
  placeholder = null,
  className,
  sizes,
  fit,
  priority = false,
  cloudName,
}: Props) {
  // Empty-string alt is allowed *only* for purely decorative repeats; null
  // means the caller forgot.
  if (alt == null) {
    throw new Error(`<BlogImage> requires alt (publicId=${publicId})`);
  }

  const { src, srcSet, sizes: defaultSizes } = cloudinarySrcSet(publicId, {
    fit,
    focalX,
    focalY,
    cloudName,
  });

  // `fit=fill` consumers (homepage hero, post-card thumb) lock the wrapper's
  // aspect with `className="aspect-[…]"` and want the image to cover. Other
  // consumers (post detail) just want the image to flow at its natural size.
  const coverFit = fit === "fill";

  return (
    <div className={cn("relative overflow-hidden bg-bg-muted", className)}>
      {placeholder && (
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage: `url(${placeholder})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            // `scale` hides the blur's soft edges inside rounded corners;
            // `blur` is what makes a 24-px LQIP look like proper bokeh.
            filter: "blur(24px) saturate(1.1)",
            transform: "scale(1.1)",
          }}
        />
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        srcSet={srcSet}
        sizes={sizes ?? defaultSizes}
        alt={alt}
        width={width}
        height={height}
        decoding="async"
        loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : "auto"}
        className={
          coverFit
            ? "absolute inset-0 h-full w-full object-cover"
            : "relative block h-auto w-full"
        }
      />
    </div>
  );
}

/** For cases where you only have the public_id and want a flat URL (OG images, etc). */
export function ogImageUrl(publicId: string, cloudName?: string): string {
  return cloudinaryUrl(publicId, { width: 1200, height: 630, fit: "fill", cloudName });
}
