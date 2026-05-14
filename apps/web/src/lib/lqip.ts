/**
 * Client-side LQIP generator. Draws the uploaded file to a 24×24 canvas,
 * exports as JPEG data URL (~1.5 KB). Used as the CSS background while the
 * full image streams in — same role as a blurhash decode.
 */

const LQIP_MAX_DIMENSION = 24;
const LQIP_QUALITY = 0.5;

export async function computeLqip(file: Blob): Promise<string | null> {
  if (typeof document === "undefined") return null;
  const bitmap = await createImageBitmap(file).catch(() => null);
  if (!bitmap) return null;
  try {
    const ratio = bitmap.width / bitmap.height;
    const w = ratio >= 1 ? LQIP_MAX_DIMENSION : Math.round(LQIP_MAX_DIMENSION * ratio);
    const h = ratio >= 1 ? Math.round(LQIP_MAX_DIMENSION / ratio) : LQIP_MAX_DIMENSION;
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, w);
    canvas.height = Math.max(1, h);
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", LQIP_QUALITY);
  } finally {
    bitmap.close?.();
  }
}
