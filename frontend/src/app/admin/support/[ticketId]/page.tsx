"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { SupportAIAssist } from "@/components/support/SupportAIAssist";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatusBadge,
  Tabs,
  Textarea,
  Timeline,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  adminAddInternalNote,
  adminAssignSupportTicket,
  adminCloseSupportTicket,
  adminEscalateSupportTicket,
  adminReplySupportTicket,
  adminReopenSupportTicket,
  adminResolveSupportTicket,
  adminUpdateSupportCategory,
  adminUpdateSupportPriority,
  adminUpdateSupportStatus,
  fetchAdminSupportTicket,
  supportTicketNumber,
} from "@/lib/support-api";
import {
  OPEN_SUPPORT_STATUSES,
  SUPPORT_PRIORITY_OPTIONS,
  SUPPORT_STATUS_OPTIONS,
  formatSupportLabel,
  priorityTone,
} from "@/lib/support-ui";
import type { SupportCase } from "@/lib/types/support";

const ESCALATION_LEVELS = [
  { value: "L1", label: "L1 — Tier 1 support" },
  { value: "L2", label: "L2 — Senior support" },
  { value: "finance", label: "Finance" },
];

export default function AdminSupportTicketDetailPage() {
  const params = useParams<{ ticketId: string }>();
  const { user } = useAuth();
  const toast = useToast();

  const [ticket, setTicket] = useState<SupportCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [escalationLevel, setEscalationLevel] = useState("L1");
  const [escalationNote, setEscalationNote] = useState("");
  const [replyBusy, setReplyBusy] = useState(false);
  const [noteBusy, setNoteBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    const data = await fetchAdminSupportTicket(params.ticketId);
    setTicket(data);
  }, [params.ticketId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load ticket",
          );
          setTicket(null);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  const timelineItems = useMemo(() => {
    if (!ticket) return [];
    return [...ticket.messages]
      .filter((m) => !m.is_internal)
      .sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      )
      .map((m) => ({
        id: m.id,
        title: m.author_name ?? "Participant",
        description: m.body,
        meta: (
          <span className="text-xs text-muted-foreground">
            {formatDateTime(m.created_at)}
          </span>
        ),
      }));
  }, [ticket]);

  async function runAction(
    label: string,
    action: () => Promise<SupportCase>,
  ) {
    setActionBusy(true);
    try {
      const updated = await action();
      setTicket(updated);
      toast.push({ tone: "success", title: label });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: `${label} failed`,
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setActionBusy(false);
    }
  }

  async function onReply() {
    const body = replyBody.trim();
    if (!body) return;
    setReplyBusy(true);
    try {
      const updated = await adminReplySupportTicket(params.ticketId, body);
      setTicket(updated);
      setReplyBody("");
      toast.push({ tone: "success", title: "Reply sent" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Reply failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setReplyBusy(false);
    }
  }

  async function onAddNote() {
    const body = noteBody.trim();
    if (!body) return;
    setNoteBusy(true);
    try {
      const updated = await adminAddInternalNote(params.ticketId, body);
      setTicket(updated);
      setNoteBody("");
      toast.push({ tone: "success", title: "Internal note added" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Note failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setNoteBusy(false);
    }
  }

  if (error) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Admin"
        title="Ticket unavailable"
        description="This support ticket could not be loaded."
        actions={
          <Link href="/admin/support">
            <Button variant="secondary">Queue</Button>
          </Link>
        }
      >
        <EmptyState title="Not found" description={error} />
      </DashboardShell>
    );
  }

  if (!ticket) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Admin"
        title="Loading ticket…"
        description="Fetching case details and message history."
      >
        <SkeletonLoader lines={6} />
      </DashboardShell>
    );
  }

  const closed =
    ticket.status === "closed" ||
    ticket.status === "archived" ||
    ticket.archived_at != null;
  const canReply = !closed;
  const showAssign = !ticket.assignee_user_id && !closed;
  const showEscalate = OPEN_SUPPORT_STATUSES.has(ticket.status);
  const showResolve = OPEN_SUPPORT_STATUSES.has(ticket.status);
  const showClose =
    ticket.status !== "closed" && ticket.status !== "archived";
  const showReopen =
    ticket.status === "resolved" ||
    ticket.status === "closed" ||
    ticket.status === "archived";

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Support"
      title={ticket.subject}
      description={`${supportTicketNumber(ticket)} · ${formatSupportLabel(ticket.category)}`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={ticket.status} />
          <Badge tone={priorityTone(ticket.priority)}>
            {formatSupportLabel(ticket.priority)}
          </Badge>
          <Link href="/admin/support">
            <Button variant="secondary" size="sm">
              Queue
            </Button>
          </Link>
        </div>
      }
    >
      {closed ? (
        <Alert tone="warning" title="Ticket closed">
          Public replies are disabled. Internal notes can still be added for
          audit.
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,320px)]">
        <div className="min-w-0 space-y-6">
          <Card className="space-y-4">
            <SectionHeader
              eyebrow="Conversation"
              title="Message timeline"
              description="Public messages visible to the requester."
            />
            {timelineItems.length > 0 ? (
              <Timeline items={timelineItems} />
            ) : (
              <EmptyState
                title="No messages yet"
                description="Replies and the opening message appear here."
              />
            )}
          </Card>

          <Card className="space-y-4">
            <SectionHeader
              eyebrow="Respond"
              title="Reply or note"
              description="Public replies go to the requester. Internal notes stay staff-only."
            />
            <SupportAIAssist
              ticketId={params.ticketId}
              canDraftReply={canReply}
              onApplyReply={(draft) => setReplyBody(draft)}
              onApplyCategory={async (slug) => {
                try {
                  const updated = await adminUpdateSupportCategory(
                    params.ticketId,
                    slug,
                  );
                  setTicket(updated);
                  toast.push({ tone: "success", title: "Category updated" });
                } catch (err) {
                  toast.push({
                    tone: "danger",
                    title: "Category update failed",
                    description:
                      err instanceof ApiError ? err.detail : "Try again",
                  });
                  throw err;
                }
              }}
              onApplyPriority={async (priority) => {
                try {
                  const updated = await adminUpdateSupportPriority(
                    params.ticketId,
                    priority,
                  );
                  setTicket(updated);
                  toast.push({ tone: "success", title: "Priority updated" });
                } catch (err) {
                  toast.push({
                    tone: "danger",
                    title: "Priority update failed",
                    description:
                      err instanceof ApiError ? err.detail : "Try again",
                  });
                  throw err;
                }
              }}
            />
            <Tabs
              defaultId="reply"
              items={[
                {
                  id: "reply",
                  label: "Reply",
                  content: (
                    <div className="space-y-3">
                      <Textarea
                        label="Public reply"
                        value={replyBody}
                        onChange={(e) => setReplyBody(e.target.value)}
                        rows={4}
                        placeholder="Write a reply the requester can read…"
                        disabled={!canReply}
                      />
                      <Button
                        disabled={!canReply || replyBusy || !replyBody.trim()}
                        onClick={() => void onReply()}
                      >
                        {replyBusy ? "Sending…" : "Send reply"}
                      </Button>
                    </div>
                  ),
                },
                {
                  id: "note",
                  label: "Internal note",
                  content: (
                    <div className="space-y-3">
                      {ticket.internal_notes.length > 0 ? (
                        <ul className="mb-2 space-y-3">
                          {ticket.internal_notes.map((note) => (
                            <li
                              key={note.id}
                              className="rounded-[var(--radius-md)] border border-border bg-surface-inset px-4 py-3 text-sm"
                            >
                              <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                                <span className="font-bold text-foreground">
                                  {note.author_name ?? "Staff"}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  {formatDateTime(note.created_at)}
                                </span>
                              </div>
                              <p className="whitespace-pre-wrap text-muted-foreground">
                                {note.body}
                              </p>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          No internal notes yet.
                        </p>
                      )}
                      <Textarea
                        label="Add note"
                        value={noteBody}
                        onChange={(e) => setNoteBody(e.target.value)}
                        rows={3}
                        placeholder="Internal context for the next agent…"
                      />
                      <Button
                        variant="secondary"
                        disabled={noteBusy || !noteBody.trim()}
                        onClick={() => void onAddNote()}
                      >
                        {noteBusy ? "Saving…" : "Add internal note"}
                      </Button>
                    </div>
                  ),
                },
              ]}
            />
          </Card>
        </div>

        <aside className="min-w-0 space-y-4">
          <Card className="space-y-3">
            <SectionHeader eyebrow="Summary" title="Ticket details" />
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Number</dt>
                <dd className="font-bold text-foreground">
                  {supportTicketNumber(ticket)}
                </dd>
              </div>
              {ticket.requester_email ? (
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Requester</dt>
                  <dd className="truncate text-foreground">
                    {ticket.requester_name ?? ticket.requester_email}
                  </dd>
                </div>
              ) : null}
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Context</dt>
                <dd className="capitalize text-foreground">
                  {formatSupportLabel(ticket.requester_context ?? "fan")}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Created</dt>
                <dd className="text-foreground">
                  {formatDateTime(ticket.created_at)}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Updated</dt>
                <dd className="text-foreground">
                  {formatDateTime(ticket.updated_at)}
                </dd>
              </div>
            </dl>
          </Card>

          <Card className="space-y-4">
            <SectionHeader eyebrow="Controls" title="Priority & status" />
            <Select
              label="Priority"
              value={ticket.priority}
              disabled={actionBusy}
              onChange={(e) =>
                void runAction("Priority updated", () =>
                  adminUpdateSupportPriority(params.ticketId, e.target.value),
                )
              }
            >
              {SUPPORT_PRIORITY_OPTIONS.filter((o) => o.value !== "all").map(
                (opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ),
              )}
            </Select>
            <Select
              label="Status"
              value={ticket.status}
              disabled={actionBusy}
              onChange={(e) =>
                void runAction("Status updated", () =>
                  adminUpdateSupportStatus(params.ticketId, e.target.value),
                )
              }
            >
              {SUPPORT_STATUS_OPTIONS.filter((o) => o.value !== "all").map(
                (opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ),
              )}
            </Select>
          </Card>

          <Card className="space-y-3">
            <SectionHeader
              eyebrow="Deflection"
              title="Help before ticket"
              description="Whether the requester saw Help suggestions first."
            />
            <p className="text-sm text-foreground">
              Suggestions shown:{" "}
              <span className="font-semibold">
                {ticket.help_suggestions_shown ? "Yes" : "No"}
              </span>
            </p>
            {ticket.deflection_meta ? (
              <div className="space-y-2 text-sm text-muted-foreground">
                {ticket.deflection_meta.topic ? (
                  <p>
                    Topic:{" "}
                    <span className="font-medium text-foreground">
                      {formatSupportLabel(ticket.deflection_meta.topic)}
                    </span>
                  </p>
                ) : null}
                {ticket.deflection_meta.suggested_article_slugs?.length ? (
                  <div>
                    <p className="font-medium text-foreground">Suggested articles</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4">
                      {ticket.deflection_meta.suggested_article_slugs.map((slug) => (
                        <li key={slug}>
                          <Link
                            href={`/help/articles/${slug}`}
                            className="text-primary-text hover:underline"
                          >
                            {slug}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {ticket.deflection_meta.articles_clicked?.length ? (
                  <p>
                    Clicked:{" "}
                    {ticket.deflection_meta.articles_clicked.join(", ")}
                  </p>
                ) : null}
                {ticket.deflection_meta.referrer ? (
                  <p className="break-all">
                    Referrer: {ticket.deflection_meta.referrer}
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No deflection metadata on this ticket.
              </p>
            )}
          </Card>

          <Card className="space-y-4">
            <SectionHeader
              eyebrow="Actions"
              title="Lifecycle"
              description="Recorded for audit."
            />
            <div className="flex flex-wrap gap-2">
              {showAssign && user?.id ? (
                <ConfirmAction
                  label="Assign to me"
                  title="Assign this ticket to you?"
                  description="You become the assignee for follow-up."
                  confirmLabel="Assign"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Ticket assigned", () =>
                      adminAssignSupportTicket(params.ticketId, user.id),
                    )
                  }
                />
              ) : null}

              {showEscalate ? (
                <ConfirmAction
                  label="Escalate"
                  title="Escalate this ticket?"
                  description="Sets status to escalated and records the level."
                  confirmLabel="Escalate"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Ticket escalated", () =>
                      adminEscalateSupportTicket(
                        params.ticketId,
                        escalationLevel,
                        escalationNote.trim() || undefined,
                      ),
                    )
                  }
                >
                  <div className="space-y-3">
                    <Select
                      label="Escalation level"
                      value={escalationLevel}
                      onChange={(e) => setEscalationLevel(e.target.value)}
                    >
                      {ESCALATION_LEVELS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </Select>
                    <Textarea
                      label="Note (optional)"
                      value={escalationNote}
                      onChange={(e) => setEscalationNote(e.target.value)}
                      rows={3}
                      placeholder="Why this needs escalation…"
                    />
                  </div>
                </ConfirmAction>
              ) : null}

              {showResolve ? (
                <ConfirmAction
                  label="Resolve"
                  title="Mark ticket resolved?"
                  description="Use when the issue is fixed. The requester can still reply unless you close."
                  confirmLabel="Resolve"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Ticket resolved", () =>
                      adminResolveSupportTicket(params.ticketId),
                    )
                  }
                />
              ) : null}

              {showClose ? (
                <ConfirmAction
                  label="Close"
                  title="Close this ticket?"
                  description="Stops public replies."
                  confirmLabel="Close"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Ticket closed", () =>
                      adminCloseSupportTicket(params.ticketId),
                    )
                  }
                />
              ) : null}

              {showReopen ? (
                <ConfirmAction
                  label="Reopen"
                  title="Reopen this ticket?"
                  description="Returns the ticket to the open queue for further work."
                  confirmLabel="Reopen"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Ticket reopened", () =>
                      adminReopenSupportTicket(params.ticketId),
                    )
                  }
                />
              ) : null}
            </div>
          </Card>
        </aside>
      </div>
    </DashboardShell>
  );
}
