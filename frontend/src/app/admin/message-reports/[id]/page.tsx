"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AdminAttachmentModeration } from "@/components/messaging/AdminAttachmentModeration";
import { MessageBubble } from "@/components/messaging/MessageBubble";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminMessageReport,
  hideAdminMessage,
  patchAdminMessageReport,
  restoreAdminMessage,
} from "@/lib/messaging-api";
import type {
  ConnectContext,
  MessageAttachment,
  MessageItem,
} from "@/lib/types/messaging";

function isHiddenMessage(m: MessageItem): boolean {
  return m.status === "hidden" || m.moderation_status === "hidden";
}

export default function AdminMessageReportDetailPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [status, setStatus] = useState("open");
  const [notes, setNotes] = useState("");
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [meta, setMeta] = useState<{
    reason: string;
    details?: string | null;
    reporter_display_name: string;
    reported_display_name: string;
    host_display_name?: string | null;
    thread_type?: string | null;
    connect_context?: ConnectContext | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!params?.id) return;
    let active = true;
    void (async () => {
      try {
        const res = await fetchAdminMessageReport(params.id);
        if (!active) return;
        setMeta({
          reason: res.reason,
          details: res.details,
          reporter_display_name: res.reporter_display_name,
          reported_display_name: res.reported_display_name,
          host_display_name: res.host_display_name,
          thread_type: res.thread_type,
          connect_context: res.connect_context,
        });
        setStatus(res.status);
        setNotes(res.admin_notes || "");
        setMessages(res.messages);
      } catch (err) {
        if (!active) return;
        setError(err instanceof ApiError ? err.detail : "Failed to load");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [params?.id]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Message report"
      description="Review reported messages. Private contact and payment data are not exposed."
      actions={
        <Link href="/admin/message-reports">
          <Button variant="secondary">All reports</Button>
        </Link>
      }
    >
      {loading ? <SkeletonLoader lines={6} /> : null}
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {meta ? (
        <>
          <Card className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-extrabold text-foreground">{meta.reason}</p>
              {meta.thread_type === "fan_fan" ? (
                <Badge tone="accent" size="sm">
                  Fan Connect
                </Badge>
              ) : null}
            </div>
            <p className="text-sm text-muted-foreground">
              {meta.reporter_display_name} reported {meta.reported_display_name}
              {meta.host_display_name ? ` · Host ${meta.host_display_name}` : ""}
            </p>
            {meta.connect_context?.context_label ? (
              <p className="text-sm text-body">
                {meta.connect_context.badge
                  ? `${meta.connect_context.badge} · `
                  : ""}
                {meta.connect_context.context_label}
              </p>
            ) : null}
            {meta.details ? (
              <p className="text-sm text-body">{meta.details}</p>
            ) : null}
          </Card>

          <Card className="space-y-3">
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="open">Open</option>
              <option value="reviewing">Reviewing</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </Select>
            <label className="block space-y-1 text-sm">
              <span className="font-semibold text-foreground">Admin notes</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-foreground"
              />
            </label>
            <Button
              disabled={saving}
              onClick={() => {
                setSaving(true);
                void patchAdminMessageReport(params.id, {
                  status,
                  admin_notes: notes,
                })
                  .then(() =>
                    toast.push({ tone: "success", title: "Report updated" }),
                  )
                  .catch((err) =>
                    toast.push({
                      tone: "danger",
                      title:
                        err instanceof ApiError
                          ? err.detail
                          : "Could not update report",
                    }),
                  )
                  .finally(() => setSaving(false));
              }}
            >
              Save
            </Button>
          </Card>

          <div className="space-y-3">
            <h3 className="font-extrabold text-foreground">Conversation</h3>
            {messages.length === 0 ? (
              <Alert tone="info" title="No messages">
                This report has no message payload to review.
              </Alert>
            ) : null}
            {messages.map((m) => {
              const hidden = isHiddenMessage(m);
              const attachments = m.attachments || [];
              return (
                <div key={m.id} className="space-y-2">
                  <MessageBubble message={m} />
                  {attachments.length > 0 ? (
                    <div className="space-y-2 pl-1">
                      <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                        Attachments
                      </p>
                      {attachments.map((a) => (
                        <AdminAttachmentModeration
                          key={a.id}
                          attachment={a}
                          onUpdated={(next: MessageAttachment) =>
                            setMessages((prev) =>
                              prev.map((x) =>
                                x.id === m.id
                                  ? {
                                      ...x,
                                      attachments: (x.attachments || []).map(
                                        (att) =>
                                          att.id === next.id ? next : att,
                                      ),
                                    }
                                  : x,
                              ),
                            )
                          }
                          onError={(message) =>
                            toast.push({ tone: "danger", title: message })
                          }
                          onSuccess={(title) =>
                            toast.push({ tone: "success", title })
                          }
                        />
                      ))}
                    </div>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    {hidden ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          void restoreAdminMessage(m.id)
                            .then(() => {
                              toast.push({
                                tone: "success",
                                title: "Message restored",
                              });
                              return fetchAdminMessageReport(params.id);
                            })
                            .then((res) => setMessages(res.messages))
                            .catch((err) =>
                              toast.push({
                                tone: "danger",
                                title:
                                  err instanceof ApiError
                                    ? err.detail
                                    : "Restore failed",
                              }),
                            )
                        }
                      >
                        Restore message
                      </Button>
                    ) : m.message_type !== "system" ? (
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() =>
                          void hideAdminMessage(m.id)
                            .then(() =>
                              fetchAdminMessageReport(params.id).then((res) => {
                                setMessages(res.messages);
                                toast.push({
                                  tone: "success",
                                  title: "Message hidden",
                                });
                              }),
                            )
                            .catch((err) =>
                              toast.push({
                                tone: "danger",
                                title:
                                  err instanceof ApiError
                                    ? err.detail
                                    : "Hide failed",
                              }),
                            )
                        }
                      >
                        Hide message
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : null}
    </DashboardShell>
  );
}
