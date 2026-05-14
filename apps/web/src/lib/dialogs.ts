/**
 * Imperative dialog API. Call `confirmDialog/promptDialog/alertDialog` from
 * anywhere - the single `<DialogHost>` mounted in a layout renders the active
 * dialog and resolves the returned Promise when the user picks.
 *
 * Why imperative: matches the native API (`window.confirm` etc.) so call sites
 * stay readable as `if (!(await confirmDialog(...))) return;`. State lives in a
 * module-scope store, so callers don't need a hook or context provider.
 */

export type DialogTone = "default" | "danger";

interface ConfirmState {
  kind: "confirm";
  title: string;
  message?: string;
  confirmLabel: string;
  cancelLabel: string;
  tone: DialogTone;
}

interface PromptState {
  kind: "prompt";
  title: string;
  message?: string;
  defaultValue: string;
  placeholder?: string;
  confirmLabel: string;
  cancelLabel: string;
  inputType: "text" | "url";
}

interface AlertState {
  kind: "alert";
  title: string;
  message?: string;
  confirmLabel: string;
  tone: DialogTone;
}

export type DialogState = ConfirmState | PromptState | AlertState;

let current: DialogState | null = null;
let resolver: ((value: unknown) => void) | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  for (const fn of listeners) fn();
}

export function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export function getCurrent(): DialogState | null {
  return current;
}

/** Internal: invoked by the DialogHost when the user picks. */
export function resolveCurrent(value: unknown): void {
  const r = resolver;
  current = null;
  resolver = null;
  emit();
  r?.(value);
}

function open<T>(state: DialogState): Promise<T> {
  // If a previous dialog is still open, cancel it so we don't lose the resolver.
  if (resolver) {
    const r = resolver;
    resolver = null;
    r(state.kind === "prompt" ? null : false);
  }
  current = state;
  emit();
  return new Promise<T>((res) => {
    resolver = res as (value: unknown) => void;
  });
}

// ---------- Public API ----------

export function confirmDialog(opts: {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: DialogTone;
}): Promise<boolean> {
  return open<boolean>({
    kind: "confirm",
    title: opts.title,
    message: opts.message,
    confirmLabel: opts.confirmLabel ?? "Confirm",
    cancelLabel: opts.cancelLabel ?? "Cancel",
    tone: opts.tone ?? "default",
  });
}

export function promptDialog(opts: {
  title: string;
  message?: string;
  defaultValue?: string;
  placeholder?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  inputType?: "text" | "url";
}): Promise<string | null> {
  return open<string | null>({
    kind: "prompt",
    title: opts.title,
    message: opts.message,
    defaultValue: opts.defaultValue ?? "",
    placeholder: opts.placeholder,
    confirmLabel: opts.confirmLabel ?? "OK",
    cancelLabel: opts.cancelLabel ?? "Cancel",
    inputType: opts.inputType ?? "text",
  });
}

export function alertDialog(opts: {
  title: string;
  message?: string;
  confirmLabel?: string;
  tone?: DialogTone;
}): Promise<void> {
  return open<void>({
    kind: "alert",
    title: opts.title,
    message: opts.message,
    confirmLabel: opts.confirmLabel ?? "OK",
    tone: opts.tone ?? "default",
  });
}
