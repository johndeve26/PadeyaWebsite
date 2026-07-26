"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui";
import { packLabel } from "@/lib/auth/impersonation-scopes";
import { cn } from "@/lib/cn";
import { formatRemainingDuration } from "@/lib/format";

/**
 * Global warning banner while a platform admin is in an audited impersonation session.
 * Mounted in the root app shell so it covers dashboard, connect, host, checkout, settings, etc.
 * Works on desktop + mobile and follows light/dark theme tokens.
 */
export function ImpersonationBanner() {
  const { isImpersonating, impersonation, user, stopImpersonation } = useAuth();
  const [busy, setBusy] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const rootRef = useRef<HTMLDivElement>(null);

  const expiresAtMs = useMemo(() => {
    const raw = impersonation?.expires_at;
    if (!raw) return null;
    const parsed = Date.parse(raw);
    return Number.isFinite(parsed) ? parsed : null;
  }, [impersonation?.expires_at]);

  useEffect(() => {
    if (!isImpersonating || expiresAtMs == null) return;
    const id = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isImpersonating, expiresAtMs]);

  useEffect(() => {
    if (!isImpersonating) {
      document.documentElement.style.removeProperty(
        "--impersonation-banner-height",
      );
      return;
    }
    const el = rootRef.current;
    if (!el) return;

    const apply = () => {
      document.documentElement.style.setProperty(
        "--impersonation-banner-height",
        `${el.offsetHeight}px`,
      );
    };
    apply();
    const ro = new ResizeObserver(apply);
    ro.observe(el);
    return () => {
      ro.disconnect();
      document.documentElement.style.removeProperty(
        "--impersonation-banner-height",
      );
    };
  }, [isImpersonating, expiresAtMs, impersonation?.impersonation_id]);

  if (!isImpersonating || !user) return null;

  async function onExit() {
    setBusy(true);
    try {
      const returnTo = await stopImpersonation();
      const targetId =
        impersonation?.target_user_id ||
        user?.impersonation?.target_user_id ||
        user?.id;
      window.location.assign(
        returnTo || (targetId ? `/admin/users/${targetId}` : "/admin/users"),
      );
    } finally {
      setBusy(false);
    }
  }

  const targetNameRaw =
    impersonation?.target_full_name?.trim() || user.full_name || null;
  const targetEmailRaw =
    impersonation?.target_email?.trim() || user.email || null;
  const displayName = targetNameRaw || targetEmailRaw || "user";
  const adminName =
    impersonation?.impersonator_full_name?.trim() ||
    impersonation?.impersonator_email ||
    "Admin";

  const remainingMs =
    expiresAtMs == null ? null : Math.max(0, expiresAtMs - nowMs);
  const remainingLabel =
    remainingMs == null ? null : formatRemainingDuration(remainingMs);
  const expired = remainingMs != null && remainingMs <= 0;
  const urgent =
    remainingMs != null && remainingMs > 0 && remainingMs <= 5 * 60 * 1000;

  const isDemoSeedTarget = (targetEmailRaw || "")
    .toLowerCase()
    .endsWith("@demo.padeye.test");

  return (
    <div
      ref={rootRef}
      role="alert"
      aria-live="polite"
      data-impersonation-banner
      data-demo-seed={isDemoSeedTarget ? "true" : "false"}
      className={cn(
        "sticky top-0 z-50 border-b-2",
        "bg-warning-surface text-warning-foreground border-warning",
        "shadow-[0_8px_24px_color-mix(in_srgb,var(--warning)_28%,transparent)]",
        "dark:shadow-[0_8px_28px_color-mix(in_srgb,var(--warning)_35%,transparent)]",
        urgent || expired
          ? "bg-danger-surface text-danger-foreground border-danger"
          : null,
      )}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.10] dark:opacity-[0.14]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(-45deg, currentColor 0 8px, transparent 8px 16px)",
        }}
        aria-hidden
      />
      <div className="relative mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6 lg:px-8">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center rounded-[var(--radius-sm)] px-2 py-0.5 text-[11px] font-extrabold uppercase tracking-[0.12em]",
                urgent || expired
                  ? "bg-danger text-paper"
                  : "bg-warning text-ink",
              )}
            >
              Audited session
            </span>
            {isDemoSeedTarget ? (
              <span className="inline-flex items-center rounded-[var(--radius-sm)] border border-current/30 bg-background/50 px-2 py-0.5 text-[11px] font-extrabold uppercase tracking-[0.12em] dark:bg-background/30">
                Demo seed account
              </span>
            ) : null}
            {remainingLabel ? (
              <span
                className={cn(
                  "font-mono text-xs font-bold tabular-nums sm:text-sm",
                  expired || urgent ? "text-danger-foreground" : null,
                )}
              >
                Time remaining: {remainingLabel}
              </span>
            ) : null}
          </div>
          <p className="text-sm font-extrabold leading-snug tracking-tight sm:text-[0.95rem]">
            Impersonating {displayName}. Pack:{" "}
            {packLabel(impersonation?.pack)}. Checkout and payouts stay blocked.
            Actions are audited.
          </p>
          <p className="flex flex-col gap-0.5 text-xs font-medium leading-snug opacity-90 sm:flex-row sm:flex-wrap sm:items-center sm:gap-0 sm:text-sm">
            <span className="min-w-0 truncate">
              Target: {targetEmailRaw}
            </span>
            <span className="mx-1.5 hidden opacity-50 sm:inline" aria-hidden>
              ·
            </span>
            <span className="min-w-0 truncate">Admin: {adminName}</span>
            {isDemoSeedTarget ? (
              <>
                <span className="mx-1.5 hidden opacity-50 sm:inline" aria-hidden>
                  ·
                </span>
                <span className="whitespace-nowrap">
                  Seed login still works separately
                </span>
              </>
            ) : null}
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="danger"
          disabled={busy}
          onClick={() => void onExit()}
          className="w-full shrink-0 sm:w-auto"
        >
          {busy ? "Ending…" : "Exit impersonation"}
        </Button>
      </div>
    </div>
  );
}
