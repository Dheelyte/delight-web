"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";

/**
 * Pre-upload crop UI. Locked to a configurable aspect ratio (default 16:9 -
 * the format covers display in most layouts). Drag the rect to reposition;
 * drag a corner to resize. Confirm produces a JPEG blob via canvas.
 *
 * Output is capped at 1920px on the long side because Cloudinary will resize
 * down anyway, and we'd rather not push a 30 MB upload through a 6 MB-limited
 * Lambda payload chain in production.
 */

type CornerHandle = "nw" | "ne" | "sw" | "se";
type DragMode = "move" | CornerHandle;

interface CropRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Drag {
  mode: DragMode;
  startClientX: number;
  startClientY: number;
  startCrop: CropRect;
}

interface Props {
  file: File;
  aspectRatio?: number;
  maxOutputWidth?: number;
  onConfirm: (blob: Blob) => void;
  onCancel: () => void;
}

export function CropDialog({
  file,
  aspectRatio = 16 / 9,
  maxOutputWidth = 1920,
  onConfirm,
  onCancel,
}: Props) {
  const [url, setUrl] = useState<string>("");
  const [container, setContainer] = useState({ w: 0, h: 0 });
  const [crop, setCrop] = useState<CropRect>({ x: 0, y: 0, w: 0, h: 0 });
  const [busy, setBusy] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const dragRef = useRef<Drag | null>(null);

  useEffect(() => {
    const objUrl = URL.createObjectURL(file);
    setUrl(objUrl);
    return () => URL.revokeObjectURL(objUrl);
  }, [file]);

  // ESC = cancel.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  // Drag handlers live on `document` so the cursor can leave the rect (or
  // even the dialog) without losing tracking. The previous setPointerCapture
  // approach broke move/resize because captured events only fire on the
  // capture target, not on the parent we'd attached the move handler to.
  useEffect(() => {
    function onMove(e: PointerEvent) {
      const drag = dragRef.current;
      if (!drag) return;
      const dx = e.clientX - drag.startClientX;
      const dy = e.clientY - drag.startClientY;

      if (drag.mode === "move") {
        const x = clamp(drag.startCrop.x + dx, 0, container.w - drag.startCrop.w);
        const y = clamp(drag.startCrop.y + dy, 0, container.h - drag.startCrop.h);
        setCrop({ ...drag.startCrop, x, y });
        return;
      }
      setCrop(resizeRect(drag.mode, drag.startCrop, dx, dy, container, aspectRatio));
    }
    function onUp() {
      dragRef.current = null;
    }
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
    document.addEventListener("pointercancel", onUp);
    return () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      document.removeEventListener("pointercancel", onUp);
    };
  }, [container, aspectRatio]);

  function initialCrop(w: number, h: number): CropRect {
    // Start at 85% of available so the user has room to drag *and* enlarge.
    const fillRatio = 0.85;
    let cw = w * fillRatio;
    let ch = cw / aspectRatio;
    if (ch > h * fillRatio) {
      ch = h * fillRatio;
      cw = ch * aspectRatio;
    }
    return { x: (w - cw) / 2, y: (h - ch) / 2, w: cw, h: ch };
  }

  function onImageLoad() {
    const img = imgRef.current;
    if (!img) return;
    const rect = img.getBoundingClientRect();
    setContainer({ w: rect.width, h: rect.height });
    setCrop(initialCrop(rect.width, rect.height));
  }

  function startDrag(mode: DragMode, e: React.PointerEvent) {
    // Prevent the browser's native image-drag behaviour from stealing the
    // gesture and switch the cursor to the chosen action.
    e.preventDefault();
    dragRef.current = {
      mode,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startCrop: { ...crop },
    };
  }

  async function confirm() {
    if (!imgRef.current || crop.w === 0) return;
    setBusy(true);
    try {
      const blob = await renderCrop({
        url,
        crop,
        container,
        naturalW: imgRef.current.naturalWidth,
        naturalH: imgRef.current.naturalHeight,
        maxOutputWidth,
      });
      if (blob) onConfirm(blob);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="crop-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
      className="fixed inset-0 z-50 grid place-items-center bg-black/60 backdrop-blur-sm p-4"
    >
      <div className="w-full max-w-3xl rounded-xl border border-border bg-bg-elevated p-5 shadow-xl">
        <h2 id="crop-title" className="font-serif text-lg">
          Crop cover image
        </h2>
        <p className="mt-1 text-sm text-fg-muted">
          Drag inside the frame to reposition; drag a corner to resize. The
          cropped region is uploaded - anything outside is discarded.
        </p>

        <div
          className="grid place-items-center overflow-hidden rounded-md bg-black"
          style={{ minHeight: "30vh" }}
        >
          {/* This inner wrap is sized to the image itself so crop.x=0 means
              "image's left edge", not "parent container's left edge". */}
          <div className="relative">
            {url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                ref={imgRef}
                src={url}
                onLoad={onImageLoad}
                alt=""
                draggable={false}
                className="block max-h-[60vh] w-auto max-w-full select-none"
              />
            )}
            {crop.w > 0 && (
              <div
                className="absolute touch-none cursor-move border-2 border-white"
                style={{
                  left: crop.x,
                  top: crop.y,
                  width: crop.w,
                  height: crop.h,
                  // Giant outer box-shadow = the scrim outside the crop rect.
                  boxShadow: "0 0 0 9999px rgba(0,0,0,0.55)",
                }}
                onPointerDown={(e) => startDrag("move", e)}
              >
                {(["nw", "ne", "sw", "se"] as CornerHandle[]).map((c) => (
                  <span
                    key={c}
                    role="button"
                    aria-label={`Resize from ${c} corner`}
                    onPointerDown={(e) => {
                      e.stopPropagation();
                      startDrag(c, e);
                    }}
                    className={cn(
                      "absolute block h-3 w-3 touch-none border border-black bg-white",
                      c === "nw" && "-left-1.5 -top-1.5 cursor-nwse-resize",
                      c === "ne" && "-right-1.5 -top-1.5 cursor-nesw-resize",
                      c === "sw" && "-bottom-1.5 -left-1.5 cursor-nesw-resize",
                      c === "se" && "-bottom-1.5 -right-1.5 cursor-nwse-resize",
                    )}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        <p className="mt-2 text-xs text-fg-subtle">
          Aspect ratio locked to 16:9.
        </p>

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-fg-muted hover:bg-bg-muted"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={confirm}
            disabled={busy || crop.w === 0}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg disabled:opacity-60"
          >
            {busy ? "Cropping…" : "Use this crop"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// helpers (kept module-local - only the dialog uses them)
// ---------------------------------------------------------------------------

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

function resizeRect(
  mode: CornerHandle,
  start: CropRect,
  dx: number,
  dy: number,
  bounds: { w: number; h: number },
  ar: number,
): CropRect {
  const signX = mode === "ne" || mode === "se" ? 1 : -1;
  const signY = mode === "se" || mode === "sw" ? 1 : -1;
  const deltaW = signX * dx;
  const deltaH = signY * dy;

  // Whichever axis the user pushed harder wins; keep the locked aspect.
  let w =
    Math.abs(deltaW) > Math.abs(deltaH * ar)
      ? start.w + deltaW
      : (start.h + deltaH) * ar;
  let h = w / ar;
  // Minimum size - prevents the rect collapsing to a dot.
  if (w < 50) {
    w = 50;
    h = w / ar;
  }

  let x = signX === -1 ? start.x + start.w - w : start.x;
  let y = signY === -1 ? start.y + start.h - h : start.y;

  // Clamp to the container, re-deriving the locked dimension when we hit a wall.
  if (x < 0) {
    w += x;
    x = 0;
    h = w / ar;
    if (signY === -1) y = start.y + start.h - h;
  }
  if (y < 0) {
    h += y;
    y = 0;
    w = h * ar;
    if (signX === -1) x = start.x + start.w - w;
  }
  if (x + w > bounds.w) {
    w = bounds.w - x;
    h = w / ar;
  }
  if (y + h > bounds.h) {
    h = bounds.h - y;
    w = h * ar;
  }
  return { x, y, w, h };
}

async function renderCrop({
  url,
  crop,
  container,
  naturalW,
  naturalH,
  maxOutputWidth,
}: {
  url: string;
  crop: CropRect;
  container: { w: number; h: number };
  naturalW: number;
  naturalH: number;
  maxOutputWidth: number;
}): Promise<Blob | null> {
  const scaleX = naturalW / container.w;
  const scaleY = naturalH / container.h;
  const sourceW = crop.w * scaleX;
  const sourceH = crop.h * scaleY;
  const outputW = Math.min(maxOutputWidth, Math.round(sourceW));
  const outputH = Math.round(outputW * (sourceH / sourceW));

  const canvas = document.createElement("canvas");
  canvas.width = outputW;
  canvas.height = outputH;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const img = new Image();
  img.src = url;
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error("Image load failed"));
  });

  ctx.drawImage(
    img,
    crop.x * scaleX,
    crop.y * scaleY,
    sourceW,
    sourceH,
    0,
    0,
    outputW,
    outputH,
  );

  return await new Promise((resolve) => {
    canvas.toBlob((b) => resolve(b), "image/jpeg", 0.92);
  });
}
