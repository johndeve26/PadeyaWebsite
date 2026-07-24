"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { cn } from "@/lib/cn";

type ToastTone = "info" | "success" | "warning" | "danger";

type ToastItem = {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
  /** Optional in-app destination — shows View action. */
  href?: string;
  onAction?: () => void;
  actionLabel?: string;
  durationMs?: number;
};

type ToastApi = {
  push: (toast: Omit<ToastItem, "id"> & { id?: string }) => void;
  dismiss: (id: string) => void;
};

const ToastContext = createContext<ToastApi | null>(null);

const toneClasses: Record<ToastTone, string> = {
  info: "border-info/40 bg-info-surface text-info-foreground",
  success: "border-success/45 bg-success-surface text-success-foreground",
  warning: "border-warning/45 bg-warning-surface text-warning-foreground",
  danger: "border-danger/45 bg-danger-surface text-danger-foreground",
};

const MAX_TOASTS = 3;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (toast: Omit<ToastItem, "id"> & { id?: string }) => {
      const id =
        toast.id ?? `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const duration =
        toast.durationMs ??
        (toast.href || toast.onAction ? 5500 : 4000);
      setItems((prev) => {
        const withoutDup = prev.filter((t) => t.id !== id);
        return [...withoutDup, { ...toast, id, tone: toast.tone }].slice(
          -MAX_TOASTS,
        );
      });
      window.setTimeout(() => dismiss(id), duration);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ push, dismiss }), [push, dismiss]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className={cn(
          "pointer-events-none fixed z-[60] flex flex-col gap-2 px-4",
          // Mobile: bottom (above bottom nav). Desktop: top-right.
          "inset-x-0 bottom-20 items-center",
          "md:inset-x-auto md:bottom-auto md:right-4 md:top-20 md:items-end",
        )}
      >
        {items.map((item) => {
          const actionable = Boolean(item.href || item.onAction);
          const actionLabel = item.actionLabel || "View";
          return (
            <div
              key={item.id}
              role="status"
              className={cn(
                "pointer-events-auto w-full max-w-sm rounded-[var(--radius-md)] border px-4 py-3 shadow-[var(--shadow)]",
                toneClasses[item.tone],
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="text-sm font-bold tracking-tight">{item.title}</p>
                  {item.description ? (
                    <p className="text-xs leading-relaxed text-current/90">
                      {item.description}
                    </p>
                  ) : null}
                  {actionable ? (
                    <button
                      type="button"
                      className="mt-2 text-[11px] font-bold underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                      onClick={() => {
                        item.onAction?.();
                        dismiss(item.id);
                      }}
                    >
                      {actionLabel}
                    </button>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="rounded-sm text-sm font-bold text-current/70 transition-colors hover:text-current focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  aria-label="Dismiss notification"
                  onClick={() => dismiss(item.id)}
                >
                  ×
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
