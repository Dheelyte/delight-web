"use client";

import { useEffect, useRef, useState } from "react";

import { CropDialog } from "./crop-dialog";
import { callApi, ClientApiError } from "@/lib/client-api";
import { cloudinaryUrl } from "@/lib/cloudinary";
import { promptDialog } from "@/lib/dialogs";
import { uploadImage, type UploadedMedia } from "@/lib/upload";

interface MediaOut {
  id: string;
  cloud_name: string;
  cloudinary_public_id: string;
  width: number;
  height: number;
  alt: string;
  placeholder_data_url: string | null;
  focal_x: number | null;
  focal_y: number | null;
}

interface Props {
  initialMediaId: string | null;
  onChange: (mediaId: string | null) => void;
}

export function CoverPicker({ initialMediaId, onChange }: Props) {
  const [media, setMedia] = useState<MediaOut | null>(null);
  // Just-uploaded `secure_url` short-circuits the URL build until next reload.
  const [secureUrl, setSecureUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Resolve the persisted cover into a MediaOut on mount / when id changes.
  useEffect(() => {
    let cancelled = false;
    setSecureUrl(null);
    if (!initialMediaId) {
      setMedia(null);
      return;
    }
    callApi<MediaOut>(`/v1/media/${initialMediaId}`)
      .then((m) => {
        if (!cancelled) setMedia(m);
      })
      .catch(() => {
        if (!cancelled) setMedia(null);
      });
    return () => {
      cancelled = true;
    };
  }, [initialMediaId]);

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    // Clear the input value so picking the same file twice still fires.
    if (fileRef.current) fileRef.current.value = "";
    if (!file) return;
    setError(null);
    setPendingFile(file);
  }

  async function onCropConfirmed(blob: Blob) {
    const file = pendingFile;
    setPendingFile(null);
    if (!file) return;

    const raw = await promptDialog({
      title: "Cover image alt text",
      message: "Describe this image for screen readers. Required.",
      placeholder: "e.g. Editorial portrait of the author",
      confirmLabel: "Save",
    });
    const alt = raw?.trim();
    if (!alt) {
      setError("Alt text is required.");
      return;
    }

    setBusy(true);
    try {
      const filename = file.name.replace(/\.[^.]+$/, "") + "-crop.jpg";
      const m: UploadedMedia = await uploadImage({
        file: blob,
        alt,
        folder: "covers",
        filename,
      });
      const next: MediaOut = {
        id: m.id,
        cloud_name: m.cloud_name,
        cloudinary_public_id: m.cloudinary_public_id,
        width: m.width,
        height: m.height,
        alt: m.alt,
        placeholder_data_url: m.placeholder_data_url,
        focal_x: null,
        focal_y: null,
      };
      setSecureUrl(m.secure_url);
      setMedia(next);
      onChange(next.id);
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : (err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function clear() {
    setMedia(null);
    setSecureUrl(null);
    onChange(null);
  }

  return (
    <div className="space-y-2">
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={onPick}
      />

      {pendingFile && (
        <CropDialog
          file={pendingFile}
          onConfirm={onCropConfirmed}
          onCancel={() => setPendingFile(null)}
        />
      )}

      {media ? (
        <>
          <div className="relative aspect-video overflow-hidden rounded-md border border-border bg-bg-muted">
            {media.placeholder_data_url && (
              <div
                aria-hidden="true"
                className="absolute inset-0"
                style={{
                  backgroundImage: `url(${media.placeholder_data_url})`,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                  // Same blur+scale recipe as <BlogImage> so the preview matches
                  // what readers see on the public site.
                  filter: "blur(24px) saturate(1.1)",
                  transform: "scale(1.1)",
                }}
              />
            )}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={
                secureUrl ??
                cloudinaryUrl(media.cloudinary_public_id, {
                  width: 600,
                  cloudName: media.cloud_name,
                })
              }
              alt={media.alt}
              className="relative block h-full w-full object-cover"
            />
          </div>
          <div className="flex justify-between gap-2 text-xs">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              className="rounded-md border border-border px-2 py-1 text-fg-muted hover:bg-bg-muted disabled:opacity-60"
            >
              Replace
            </button>
            <button
              type="button"
              onClick={clear}
              className="text-fg-muted hover:text-fg"
            >
              Remove cover
            </button>
          </div>
        </>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
          className="block w-full rounded-md border border-dashed border-border bg-bg p-6 text-xs text-fg-muted hover:bg-bg-muted disabled:opacity-60"
        >
          {busy ? "Uploading…" : "Choose cover image"}
        </button>
      )}

      {error && (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
