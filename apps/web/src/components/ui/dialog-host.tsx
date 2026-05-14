"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { cn } from "@/lib/cn";
import {
  type DialogState,
  getCurrent,
  resolveCurrent,
  subscribe,
} from "@/lib/dialogs";

/**
 * Renders the active dialog from the module store. Mount once near the root
 * of a layout. The component handles: focus capture, ESC-to-cancel,
 * backdrop-click-to-cancel, and form submit (Enter) on the prompt variant.
 */
export function DialogHost() {
  const state = useSyncExternalStore<DialogState | null>(
    subscribe,
    getCurrent,
    () => null,
  );
  if (!state) return null;
  return <Dialog state={state} />;
}

function Dialog({ state }: { state: DialogState }) {
  const [value, setValue] = useState(
    state.kind === "prompt" ? state.defaultValue : "",
  );
  const inputRef = useRef<HTMLInputElement | null>(null);
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        cancel();
      }
    }
    document.addEventListener("keydown", onKey);
    // Move focus into the dialog.
    queueMicrotask(() => {
      if (state.kind === "prompt") {
        inputRef.current?.focus();
        inputRef.current?.select();
      } else {
        cancelRef.current?.focus();
      }
    });
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  function cancel() {
    if (state.kind === "alert") {
      resolveCurrent(undefined);
    } else if (state.kind === "prompt") {
      resolveCurrent(null);
    } else {
      resolveCurrent(false);
    }
  }

  function confirm() {
    if (state.kind === "alert") {
      resolveCurrent(undefined);
    } else if (state.kind === "prompt") {
      resolveCurrent(value);
    } else {
      resolveCurrent(true);
    }
  }

  function onBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) cancel();
  }

  const tone =
    state.kind === "prompt"
      ? "default"
      : (state as { tone: "default" | "danger" }).tone;
  const confirmClass = cn(
    "rounded-md px-3 py-1.5 text-sm font-medium",
    tone === "danger"
      ? "bg-red-600 text-white hover:bg-red-700"
      : "bg-accent text-accent-fg hover:opacity-90",
  );

  return (
    <div
      role="presentation"
      onClick={onBackdropClick}
      className="fixed inset-0 z-50 grid place-items-center bg-black/40 backdrop-blur-sm"
    >
      <div
        ref={dialogRef}
        role={state.kind === "alert" ? "alertdialog" : "dialog"}
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby={state.message ? "dialog-message" : undefined}
        className="w-full max-w-sm rounded-xl border border-border bg-bg-elevated p-5 shadow-xl"
      >
        <h2 id="dialog-title" className="font-serif text-lg">
          {state.title}
        </h2>
        {state.message && (
          <p id="dialog-message" className="mt-2 text-sm text-fg-muted">
            {state.message}
          </p>
        )}

        {state.kind === "prompt" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              confirm();
            }}
            className="mt-3"
          >
            <input
              ref={inputRef}
              type={state.inputType}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={state.placeholder}
              className="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </form>
        )}

        <div className="mt-5 flex justify-end gap-2">
          {state.kind !== "alert" && (
            <button
              ref={cancelRef}
              type="button"
              onClick={cancel}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-fg-muted hover:bg-bg-muted"
            >
              {(state as { cancelLabel: string }).cancelLabel}
            </button>
          )}
          <button type="button" onClick={confirm} className={confirmClass}>
            {state.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
