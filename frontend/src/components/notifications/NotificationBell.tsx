"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useRef, useState, type MouseEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui";
import { useUnreadNotifications } from "@/hooks/useUnreadNotifications";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import {
  archiveNotification,
  fetchUnreadNotificationPreview,
  markAllNotificationsRead,
  markNotificationRead,
  notificationsInboxHref,
  notifyNotificationsChanged,
  type InAppNotification,
} from "@/lib/notifications-api";
import {
  safeToastActionHref,
  safeToastCopy,
  notificationKindLabel,
} from "@/lib/notifications-toast";

const PREVIEW_LIMIT = 8;

/**
 * Header bell — dropdown preview of unread alerts only; full history via “View all”.
 */
export function NotificationBell({
  className,
  tone = "default",
}: {
  className?: string;
  tone?: "default" | "onDark";
}) {
  const { user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const unread = useUnreadNotifications();

  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<InAppNotification[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);

  const inboxHref = notificationsInboxHref(pathname || "");
  const active =
    pathname === "/dashboard/notifications" ||
    pathname?.startsWith("/dashboard/notifications/") ||
    pathname === "/host/notifications" ||
    pathname?.startsWith("/host/notifications/");

  const loadPreview = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setLoadError(null);
    try {
      const data = await fetchUnreadNotificationPreview(PREVIEW_LIMIT);
      setItems(data.items);
    } catch {
      setLoadError("Could not load alerts.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!open) return;
    void loadPreview();
  }, [open, loadPreview]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      const target = event.target as Node | null;
      if (rootRef.current && target && !rootRef.current.contains(target)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!user) return null;

  async function openNotification(row: InAppNotification) {
    const href = safeToastActionHref(row.link_path, inboxHref);
    setOpen(false);
    try {
      if (!row.read_at) {
        await markNotificationRead(row.id);
        notifyNotificationsChanged();
      }
    } catch {
      /* navigate anyway */
    }
    router.push(href);
  }

  async function onDismiss(row: InAppNotification, event: MouseEvent) {
    event.stopPropagation();
    event.preventDefault();
    setActionBusy(true);
    try {
      await archiveNotification(row.id);
      setItems((prev) => prev.filter((item) => item.id !== row.id));
      notifyNotificationsChanged();
    } catch {
      setLoadError("Could not dismiss this alert.");
    } finally {
      setActionBusy(false);
    }
  }

  async function onMarkAllRead() {
    setActionBusy(true);
    setLoadError(null);
    try {
      await markAllNotificationsRead();
      setItems([]);
      notifyNotificationsChanged();
    } catch {
      setLoadError("Could not mark all alerts as read.");
    } finally {
      setActionBusy(false);
    }
  }

  const buttonClass = cn(
    "relative inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-sm)] border text-sm font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2",
    tone === "onDark"
      ? cn(
          "border-paper/30 focus-visible:ring-offset-ink",
          active || open
            ? "bg-paper text-ink"
            : "bg-transparent text-paper hover:border-paper/55 hover:bg-paper/10",
        )
      : cn(
          "border-border hover:border-border-strong focus-visible:ring-offset-background",
          active || open ? "bg-ink text-paper" : "bg-card text-foreground",
        ),
    className,
  );

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className={buttonClass}
        aria-label={
          unread > 0 ? `Notifications, ${unread} unread` : "Notifications"
        }
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <svg
          viewBox="0 0 24 24"
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          aria-hidden
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2c0 .5-.2 1-.6 1.4L4 17h5m6 0a3 3 0 1 1-6 0m6 0H9"
          />
        </svg>
        {unread > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-sm bg-primary px-1 text-[10px] font-bold text-primary-foreground">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <>
          <div
            className="fixed inset-0 z-[45] bg-ink/20 md:bg-transparent"
            aria-hidden
            onClick={() => setOpen(false)}
          />
          <div
            id={panelId}
            role="dialog"
            aria-label="New notifications"
            className={cn(
              "fixed z-50 flex max-h-[min(75vh,32rem)] w-[min(calc(100vw-1.5rem),32rem)] flex-col overflow-hidden rounded-[var(--radius-md)] border border-border bg-card shadow-[var(--shadow-strong)] sm:min-w-[20rem]",
              "right-2 top-[calc(4.25rem+env(safe-area-inset-top))] sm:absolute sm:right-0 sm:top-full sm:mt-2",
            )}
          >
            <div className="flex items-start justify-between gap-2 border-b border-border px-3 py-2.5">
              <div className="min-w-0">
                <p className="text-sm font-bold text-foreground">New alerts</p>
                <p className="text-xs text-muted-foreground">
                  Unread alerts only — tickets, merch, and updates. Chat lives in
                  Messages.
                </p>
              </div>
              {items.length > 0 || unread > 0 ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="shrink-0 text-xs"
                  disabled={actionBusy || (items.length === 0 && unread < 1)}
                  onClick={() => void onMarkAllRead()}
                >
                  Mark all read
                </Button>
              ) : null}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {loading ? (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                  Loading…
                </p>
              ) : loadError ? (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                  {loadError}
                </p>
              ) : items.length === 0 ? (
                <div className="px-3 py-8 text-center">
                  <p className="text-sm font-semibold text-foreground">
                    No new notifications
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    You&apos;re all caught up. Older alerts live in your inbox.
                  </p>
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {items.map((row) => {
                    const copy = safeToastCopy({
                      kind: row.kind,
                      title: row.title,
                      body: row.body,
                    });
                    return (
                      <li key={row.id} className="flex items-stretch gap-0">
                        <button
                          type="button"
                          className="flex shrink-0 items-start px-2.5 pt-3.5 text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus-ring disabled:opacity-50"
                          aria-label={`Dismiss ${copy.title}`}
                          disabled={actionBusy}
                          onClick={(event) => void onDismiss(row, event)}
                        >
                          <svg
                            viewBox="0 0 24 24"
                            className="h-4 w-4"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            aria-hidden
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M6 18 18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                        <button
                          type="button"
                          className="flex min-w-0 flex-1 flex-col gap-1 py-3.5 pr-4 text-left transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus-ring"
                          onClick={() => void openNotification(row)}
                        >
                          <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                            {notificationKindLabel(row.kind)}
                          </span>
                          <span className="text-sm font-semibold text-foreground">
                            {copy.title}
                          </span>
                          {copy.description ? (
                            <span className="line-clamp-2 text-xs text-muted-foreground">
                              {copy.description}
                            </span>
                          ) : null}
                          <span className="text-[10px] text-muted-foreground/80">
                            {formatDateTime(row.created_at)}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="flex flex-col gap-2 border-t border-border bg-surface/40 p-2">
              {unread > PREVIEW_LIMIT && items.length > 0 ? (
                <p className="px-1 text-center text-[10px] text-muted-foreground">
                  Showing {items.length} of {unread} unread
                </p>
              ) : null}
              <Link href={inboxHref} onClick={() => setOpen(false)}>
                <Button size="sm" variant="secondary" className="w-full">
                  View all notifications
                </Button>
              </Link>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
