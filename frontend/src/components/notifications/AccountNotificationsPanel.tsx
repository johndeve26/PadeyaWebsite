"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, useTransition } from "react";

import { Alert, Badge, Button, EmptyState } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type InAppNotification,
  type NotificationCategory,
} from "@/lib/notifications-api";
import { notificationKindLabel } from "@/lib/notifications-toast";

const FILTERS: { key: NotificationCategory; label: string }[] = [
  { key: "all", label: "All" },
  { key: "tickets", label: "Tickets" },
  { key: "merch", label: "Merch" },
  { key: "fan_connect", label: "Fan Connect" },
  { key: "host", label: "Host" },
  { key: "sponsor", label: "Sponsor" },
  { key: "admin", label: "Admin" },
];

function actionHref(row: InAppNotification): string {
  const path = (row.link_path || "").trim();
  if (!path.startsWith("/") || path.startsWith("//")) {
    return "/dashboard/notifications";
  }
  if (/^\/(vault|checkout)(\/|$)/i.test(path)) {
    return "/dashboard/notifications";
  }
  return path;
}

export function AccountNotificationsPanel({
  settingsHref = "/dashboard/settings/notifications",
  listFallbackHref = "/dashboard/notifications",
}: {
  settingsHref?: string;
  listFallbackHref?: string;
}) {
  const router = useRouter();
  const [items, setItems] = useState<InAppNotification[]>([]);
  const [total, setTotal] = useState(0);
  const [unread, setUnread] = useState(0);
  const [category, setCategory] = useState<NotificationCategory>("all");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pending, startTransition] = useTransition();

  const load = useCallback(async (cat: NotificationCategory) => {
    const data = await fetchNotifications({ limit: 80, category: cat });
    setItems(data.items);
    setTotal(data.total);
    setUnread(data.unread_count);
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load(category);
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load notifications",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [category, load]);

  function selectCategory(next: NotificationCategory) {
    startTransition(() => setCategory(next));
  }

  async function openNotification(row: InAppNotification) {
    const href = actionHref(row);
    setBusy(true);
    try {
      if (!row.read_at) {
        await markNotificationRead(row.id);
        setItems((prev) =>
          prev.map((item) =>
            item.id === row.id
              ? { ...item, read_at: new Date().toISOString() }
              : item,
          ),
        );
        setUnread((n) => Math.max(0, n - 1));
      }
    } catch {
      /* still navigate */
    } finally {
      setBusy(false);
    }
    if (href !== listFallbackHref || row.link_path) {
      router.push(href);
    }
  }

  async function onMarkRead(row: InAppNotification) {
    setBusy(true);
    try {
      await markNotificationRead(row.id);
      await load(category);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not mark as read");
    } finally {
      setBusy(false);
    }
  }

  async function onMarkAllRead() {
    setBusy(true);
    setError(null);
    try {
      await markAllNotificationsRead();
      await load(category);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not mark all read");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {unread > 0 ? (
            <>
              <span className="font-semibold text-foreground">{unread}</span> unread
              {category !== "all" ? " in this filter" : ""}
              {total > 0 ? ` · ${total} shown` : null}
            </>
          ) : (
            <>{total > 0 ? `${total} notifications` : "No unread alerts"}</>
          )}
          {pending ? " · Updating…" : null}
        </p>
        <Button
          size="sm"
          variant="ghost"
          disabled={busy || unread < 1}
          onClick={() => void onMarkAllRead()}
        >
          Mark all read
        </Button>
      </div>

      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="Notification filters"
      >
        {FILTERS.map((filter) => {
          const active = category === filter.key;
          return (
            <button
              key={filter.key}
              type="button"
              role="tab"
              aria-selected={active}
              className={cn(
                "rounded-[var(--radius-sm)] border px-3 py-1.5 text-sm font-semibold transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
                active
                  ? "border-ink bg-ink text-paper"
                  : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-foreground",
              )}
              onClick={() => selectCategory(filter.key)}
            >
              {filter.label}
            </button>
          );
        })}
      </div>

      {items.length === 0 ? (
        <EmptyState
          title={category === "all" ? "No notifications yet" : "Nothing in this filter"}
          description={
            category === "all"
              ? "Ticket, merch, Fan Connect (not chat), and host alerts appear here. New messages live under Messages."
              : "Try another filter, or check back after activity on Pàdéyá."
          }
        />
      ) : (
        <ul className="max-w-2xl divide-y divide-border border-y border-border">
          {items.map((row) => {
            const unreadRow = !row.read_at;
            return (
              <li key={row.id}>
                <div
                  className={cn(
                    "flex flex-wrap items-start justify-between gap-3 py-4",
                    unreadRow ? "bg-surface/60" : "",
                  )}
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                    onClick={() => void openNotification(row)}
                    disabled={busy}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      {unreadRow ? (
                        <Badge tone="accent" size="sm">
                          New
                        </Badge>
                      ) : null}
                      <Badge tone="neutral" size="sm">
                        {notificationKindLabel(row.kind)}
                      </Badge>
                      <span className="font-semibold text-foreground">
                        {row.title}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{row.body}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateTime(row.created_at)}
                      {row.link_path ? " · Tap to open" : ""}
                    </p>
                  </button>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busy}
                      onClick={() => void openNotification(row)}
                    >
                      Open
                    </Button>
                    {unreadRow ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => void onMarkRead(row)}
                      >
                        Mark read
                      </Button>
                    ) : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <p className="max-w-2xl text-sm text-muted-foreground">
        Browser push is optional.{" "}
        <Link
          href={settingsHref}
          className="font-semibold text-foreground underline-offset-2 hover:underline"
        >
          Manage alert preferences
        </Link>
        .
      </p>
    </>
  );
}
