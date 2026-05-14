/**
 * Client helper that performs the full Cloudinary upload + media-row creation.
 * Server signs the upload; the browser PUTs to Cloudinary directly.
 */

import { callApi } from "@/lib/client-api";
import { computeLqip } from "@/lib/lqip";

interface SignResp {
  cloud_name: string;
  api_key: string;
  timestamp: number;
  signature: string;
  folder: string | null;
}

interface CloudinaryUploadResp {
  public_id: string;
  width: number;
  height: number;
  format: string;
  bytes: number;
  secure_url: string;
}

export interface UploadedMedia {
  id: string;
  cloud_name: string;
  cloudinary_public_id: string;
  width: number;
  height: number;
  format: string;
  bytes: number;
  placeholder_data_url: string | null;
  focal_x: number | null;
  focal_y: number | null;
  alt: string;
  secure_url: string;
}

export interface UploadOptions {
  /** Original `File` or a `Blob` produced by a crop step. */
  file: File | Blob;
  alt: string;
  folder?: string;
  /** Filename for Cloudinary's `original_filename`. Defaults to `file.name`
   *  for File, or `"upload.jpg"` for a bare Blob. */
  filename?: string;
}

function inferFilename(file: File | Blob, override?: string): string {
  if (override) return override;
  if (file instanceof File && file.name) return file.name;
  return "upload.jpg";
}

export async function uploadImage(opts: UploadOptions): Promise<UploadedMedia> {
  if (!opts.alt.trim()) {
    throw new Error("Alt text is required.");
  }

  const placeholder = await computeLqip(opts.file);

  const sign = await callApi<SignResp>("/v1/media/sign", {
    method: "POST",
    body: JSON.stringify({ folder: opts.folder ?? "posts" }),
  });

  const fd = new FormData();
  fd.append("file", opts.file, inferFilename(opts.file, opts.filename));
  fd.append("api_key", sign.api_key);
  fd.append("timestamp", String(sign.timestamp));
  fd.append("signature", sign.signature);
  if (sign.folder) fd.append("folder", sign.folder);

  const cld = await fetch(
    `https://api.cloudinary.com/v1_1/${sign.cloud_name}/auto/upload`,
    { method: "POST", body: fd },
  );
  if (!cld.ok) {
    const detail = await cld.text();
    throw new Error(`Cloudinary upload failed: ${detail.slice(0, 200)}`);
  }
  const up = (await cld.json()) as CloudinaryUploadResp;

  const media = await callApi<{
    id: string;
    cloud_name: string;
    cloudinary_public_id: string;
    width: number;
    height: number;
    format: string;
    bytes: number;
    placeholder_data_url: string | null;
    focal_x: number | null;
    focal_y: number | null;
    alt: string;
  }>("/v1/media", {
    method: "POST",
    body: JSON.stringify({
      cloudinary_public_id: up.public_id,
      width: up.width,
      height: up.height,
      format: up.format,
      bytes: up.bytes,
      blurhash: null,
      placeholder_data_url: placeholder,
      alt: opts.alt.trim(),
    }),
  });

  return { ...media, secure_url: up.secure_url };
}
