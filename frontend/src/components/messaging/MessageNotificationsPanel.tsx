"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Alert,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { fetchMessageNotifications } from "@/lib/messaging-api";
import type { MessageNotification } from "@/lib/types/messaging";

export function MessageNotificationsPanel() {
  const [items, setItems] = useState<MessageNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetchMessageNotifications();
        if (!active) return;
        setItems(res.items);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Failed to load notifications",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (loading) return <SkeletonLoader lines={6} />;
  if (error) {
    return (
      <Alert tone="danger" title="Could not load">
        {error}
      </Alert>
    );
  }
  if (!items.length) {
    return (
      <EmptyState
        title="No notifications yet"
        description="Seeded message notices appear here with safe summaries only."
      />
    );
  }

  return (
    <ul className="mx-auto max-w-2xl space-y-3">
      {items.map((n) => {
        const unread = !n.read_at;
        const body = (
          <Card
            className={`space-y-1 ${unread ? "border-primary/40" : ""}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-extrabold text-foreground">{n.title}</p>
              {unread ? (
                <span className="text-[10px] font-bold uppercase tracking-wide text-primary">
                  Unread
                </span>
              ) : null}
            </div>
            <p className="text-sm text-muted-foreground">{n.body}</p>
            <p className="text-[11px] text-muted-foreground">
              {formatDate(n.created_at)}
              {n.kind ? ` · ${n.kind}` : ""}
            </p>
          </Card>
        );
        if (!n.link_path) {
          return <li key={n.id}>{body}</li>;
        }
        return (
          <li key={n.id}>
            <Link
              href={n.link_path}
              className="block transition-opacity hover:opacity-90"
            >
              {body}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
