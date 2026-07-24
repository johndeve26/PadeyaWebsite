"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  SectionHeader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  cancelAnnouncement,
  dispatchAnnouncementEmail,
  fetchAnnouncement,
  fetchAnnouncements,
} from "@/lib/crm-api";
import type { Announcement } from "@/lib/types/crm";

export default function HostAnnouncementsPage() {
  const toast = useToast();
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<Announcement[]>([]);
  const [selected, setSelected] = useState<Announcement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function load() {
    setRows(await fetchAnnouncements());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load announcements");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const id = searchParams.get("id");
    if (!id) return;
    const emailed = searchParams.get("emailed");
    const skipped = searchParams.get("skipped");
    const hasDispatchNote = emailed !== null && skipped !== null;
    if (hasDispatchNote) {
      setNote(`Emailed ${emailed}, skipped ${skipped}.`);
    }
    void (async () => {
      try {
        await load();
      } catch {
        /* list refresh is best-effort when deep-linking */
      }
      await openDetail(id, { preserveNote: hasDispatchNote });
    })();
  }, [searchParams]);

  async function openDetail(id: string, options?: { preserveNote?: boolean }) {
    setError(null);
    if (!options?.preserveNote) {
      setNote(null);
    }
    try {
      setSelected(await fetchAnnouncement(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load announcement");
    }
  }

  async function onDispatch(id: string) {
    setError(null);
    setNote(null);
    try {
      const result = await dispatchAnnouncementEmail(id);
      setNote(`Emailed ${result.emailed}, skipped ${result.skipped} (${result.delivery_status})`);
      setSelected(await fetchAnnouncement(id));
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Dispatch failed");
    }
  }

  async function onCancel(id: string) {
    setError(null);
    setNote(null);
    try {
      setSelected(await cancelAnnouncement(id));
      setNote("Announcement cancelled.");
      toast.push({ tone: "success", title: "Announcement cancelled" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Cancel failed");
      throw err;
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Audience"
        title="Announcements"
        description="Draft email and WhatsApp copy. Email requires SMTP (not dev/log mode) to reach inboxes."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/audience">
              <Button variant="secondary">Audience</Button>
            </Link>
            <Link href="/host/announcements/new">
              <Button>New announcement</Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}
        {note ? (
          <Alert tone="success" title="Dispatch complete">
            {note}
          </Alert>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="space-y-4">
            <SectionHeader title="History" description="Past broadcasts and drafts." />
            {rows.length === 0 ? (
              <EmptyState
                title="No announcements yet"
                description="Compose a broadcast to reach your audience segments."
                action={
                  <Link href="/host/announcements/new">
                    <Button>New announcement</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-border">
                {rows.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate font-bold text-foreground">{a.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {a.channel} · {a.recipient_count} recipients · {a.delivery_status}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant={selected?.id === a.id ? "primary" : "secondary"}
                      onClick={() => void openDetail(a.id)}
                    >
                      Open
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {selected ? (
            <Card className="space-y-5">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-lg font-extrabold text-foreground">{selected.title}</h3>
                  <StatusBadge status={selected.status} />
                  <StatusBadge status={selected.delivery_status} />
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <Badge tone="outline">{selected.channel}</Badge>
                  <span>{selected.recipient_count} recipients</span>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  Email body
                </p>
                <p className="whitespace-pre-wrap rounded-[var(--radius-md)] bg-muted/60 p-4 text-sm leading-relaxed text-foreground">
                  {selected.body_email}
                </p>
              </div>

              {selected.body_whatsapp ? (
                <div className="space-y-2">
                  <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    WhatsApp body
                  </p>
                  <p className="whitespace-pre-wrap rounded-[var(--radius-md)] bg-muted/60 p-4 text-sm leading-relaxed text-foreground">
                    {selected.body_whatsapp}
                  </p>
                </div>
              ) : null}

              {selected.whatsapp_export ? (
                <div className="space-y-2">
                  <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    WhatsApp export
                  </p>
                  <pre className="overflow-x-auto rounded-[var(--radius-md)] bg-ink p-4 text-xs leading-relaxed whitespace-pre-wrap text-subtle-foreground">
                    {selected.whatsapp_export}
                  </pre>
                </div>
              ) : null}

              <div className="space-y-2">
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                  Recipients ({selected.recipients.length})
                </p>
                <ul className="max-h-48 overflow-y-auto rounded-[var(--radius-md)] border border-border divide-y divide-border text-xs">
                  {selected.recipients.map((r) => (
                    <li key={r.id} className="flex flex-wrap justify-between gap-2 px-3 py-2">
                      <span className="font-semibold text-foreground">
                        {r.display_name} · {r.email}
                      </span>
                      <span className="text-muted-foreground">
                        {r.status}
                        {r.skip_reason ? ` (${r.skip_reason})` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {(selected.channel === "email" || selected.channel === "both") &&
              selected.delivery_status === "not_sent" &&
              selected.status !== "cancelled" ? (
                <Alert
                  tone="info"
                  title="Ready to send"
                  action={
                    <Button onClick={() => void onDispatch(selected.id)}>
                      Dispatch email
                    </Button>
                  }
                >
                  Email goes to marketing opt-in recipients only. Opt-in after
                  you created this draft is picked up when you dispatch.
                </Alert>
              ) : null}

              {["draft", "scheduled"].includes(selected.status) ? (
                <ConfirmAction
                  label="Cancel announcement"
                  title="Cancel this announcement?"
                  description="Draft/scheduled announcements will not be sent. Sent announcements cannot be cancelled from here."
                  confirmLabel="Cancel announcement"
                  tone="danger"
                  onConfirm={() => onCancel(selected.id)}
                />
              ) : null}
            </Card>
          ) : (
            <Card variant="muted" className="flex items-center justify-center py-16">
              <p className="text-sm text-muted-foreground">
                Select an announcement to preview content and recipients.
              </p>
            </Card>
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
