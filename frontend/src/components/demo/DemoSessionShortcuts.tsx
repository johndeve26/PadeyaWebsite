"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Alert, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchConnections } from "@/lib/fan-connect-api";
import {
  fetchAdminMessageReports,
  fetchFanThreads,
} from "@/lib/messaging-api";
import { lookupAdminUserByEmail } from "@/lib/admin-lifecycle-api";

const DEMO_PASSWORD = "DemoPass123!";

export type DemoSessionShortcut = {
  label: string;
  email: string;
  /**
   * Destination after login.
   * Special: `"reported-thread"` | `"fan-fan-thread"` | `"tolu-maze-thread"` |
   * `"pinned-demo-thread"` | `"starred-messages"` | `"impersonate:<email>"`.
   */
  href: string;
  hint?: string;
};

export type DemoSessionShortcutGroup = {
  title: string;
  description: string;
  shortcuts: DemoSessionShortcut[];
};

async function resolveFanThreadId(
  match: (thread: {
    id: string;
    thread_type?: string;
    subject?: string | null;
    counterpart?: { display_name?: string };
    related_event?: { title?: string | null } | null;
  }) => boolean,
): Promise<string | null> {
  try {
    const inbox = await fetchFanThreads({});
    const hit = inbox.items.find(match);
    return hit?.id ?? null;
  } catch {
    return null;
  }
}

async function resolveHref(href: string): Promise<string> {
  if (href === "reported-thread") {
    try {
      const res = await fetchAdminMessageReports();
      const preferred =
        res.items.find((r) => r.status === "reviewing") ||
        res.items.find((r) => r.status === "open") ||
        res.items[0];
      if (preferred) return `/admin/message-reports/${preferred.id}`;
    } catch {
      /* fall through */
    }
    return "/admin/message-reports";
  }
  if (href === "fan-fan-thread") {
    try {
      const id = await resolveFanThreadId((t) => t.thread_type === "fan_fan");
      if (id) return `/dashboard/messages/${id}`;
      const connections = await fetchConnections();
      const withThread = connections.items.find((c) => c.thread_id);
      if (withThread?.thread_id) {
        return `/dashboard/messages/${withThread.thread_id}`;
      }
    } catch {
      /* fall through */
    }
    return "/dashboard/messages";
  }
  if (href === "tolu-maze-thread" || href === "pinned-demo-thread") {
    const id = await resolveFanThreadId((t) => {
      const name = (t.counterpart?.display_name || "").toLowerCase();
      const subject = (t.subject || "").toLowerCase();
      const event = (t.related_event?.title || "").toLowerCase();
      return (
        name.includes("dj maze") ||
        subject.includes("afrobeats") ||
        event.includes("afrobeats")
      );
    });
    if (id) return `/dashboard/messages/${id}`;
    return "/dashboard/messages";
  }
  if (href === "starred-messages") {
    return "/dashboard/messages?filter=starred";
  }
  if (href.startsWith("impersonate:")) {
    const targetEmail = href.slice("impersonate:".length).trim();
    try {
      const row = await lookupAdminUserByEmail(targetEmail);
      return `/admin/users/${row.id}`;
    } catch {
      return "/admin/users";
    }
  }
  return href;
}

export function DemoSessionShortcuts({
  groups,
}: {
  groups: DemoSessionShortcutGroup[];
}) {
  const { login } = useAuth();
  const router = useRouter();
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function openAs(shortcut: DemoSessionShortcut) {
    const key = `${shortcut.email}:${shortcut.href}:${shortcut.label}`;
    setBusyKey(key);
    setError(null);
    try {
      await login(shortcut.email, DEMO_PASSWORD);
      const next = await resolveHref(shortcut.href);
      router.push(next);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not switch demo session. Is the API seeded and running?",
      );
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-4">
      {error ? (
        <Alert tone="danger" title="Demo session failed">
          {error}
        </Alert>
      ) : null}
      <div className="grid gap-4 md:grid-cols-3">
        {groups.map((group) => (
          <Card key={group.title} variant="dark" className="space-y-3">
            <div>
              <h3 className="font-extrabold text-paper">{group.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-subtle-foreground">
                {group.description}
              </p>
            </div>
            <ul className="space-y-2">
              {group.shortcuts.map((shortcut) => {
                const key = `${shortcut.email}:${shortcut.href}:${shortcut.label}`;
                const busy = busyKey === key;
                return (
                  <li key={key}>
                    <button
                      type="button"
                      disabled={busyKey !== null}
                      onClick={() => void openAs(shortcut)}
                      className="w-full rounded-[var(--radius-sm)] border border-paper/40 px-3 py-2.5 text-left transition-colors hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      <span className="block text-sm font-bold text-paper">
                        {busy ? "Signing in…" : shortcut.label}
                      </span>
                      <span className="mt-0.5 block break-all font-mono text-[11px] text-accent">
                        {shortcut.email}
                      </span>
                      {shortcut.hint ? (
                        <span className="mt-0.5 block text-[11px] text-subtle-foreground">
                          {shortcut.hint}
                        </span>
                      ) : null}
                    </button>
                  </li>
                );
              })}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  );
}
