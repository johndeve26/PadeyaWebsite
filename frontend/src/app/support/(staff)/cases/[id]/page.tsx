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
  PageToolbar,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  Timeline,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  addSupportNote,
  archiveSupportCase,
  assignSupportCase,
  closeSupportCase,
  escalateSupportCase,
  fetchSupportCase,
  replySupportCase,
  resolveSupportCase,
  updateSupportCaseCategory,
  updateSupportCasePriority,
} from "@/lib/support-api";
import type { SupportCase } from "@/lib/types/support";

const OPEN_STATUSES = new Set([
  "open",
  "in_progress",
  "waiting_on_user",
  "escalated",
]);

const ESCALATION_LEVELS = [
  { value: "L1", label: "L1 — Tier 1 support" },
  { value: "L2", label: "L2 — Senior support" },
  { value: "finance", label: "Finance" },
];

function priorityTone(priority: string): "neutral" | "warning" | "danger" {
  const key = priority.toLowerCase();
  if (key === "urgent") return "danger";
  if (key === "high") return "warning";
  return "neutral";
}

function isCaseClosed(caseItem: SupportCase): boolean {
  return (
    caseItem.status === "closed" ||
    caseItem.status === "archived" ||
    caseItem.archived_at != null
  );
}

export default function SupportCaseDetailPage() {
  const params = useParams<{ id: string }>();
  const { user } = useAuth();
  const toast = useToast();

  const [caseItem, setCaseItem] = useState<SupportCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [escalationLevel, setEscalationLevel] = useState("L1");
  const [escalationNote, setEscalationNote] = useState("");
  const [replyBusy, setReplyBusy] = useState(false);
  const [noteBusy, setNoteBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    const data = await fetchSupportCase(params.id);
    setCaseItem(data);
  }, [params.id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load support case",
          );
          setCaseItem(null);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  const timelineItems = useMemo(() => {
    if (!caseItem) return [];
    return [...caseItem.messages]
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
  }, [caseItem]);

  async function runAction(
    label: string,
    action: () => Promise<SupportCase>,
  ) {
    setActionBusy(true);
    try {
      const updated = await action();
      setCaseItem(updated);
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
      const updated = await replySupportCase(params.id, body);
      setCaseItem(updated);
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
      const updated = await addSupportNote(params.id, body);
      setCaseItem(updated);
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
        eyebrow="Support"
        title="Case unavailable"
        description="This support case could not be loaded."
        actions={
          <Link href="/support/cases">
            <Button variant="secondary">All cases</Button>
          </Link>
        }
      >
        <EmptyState title="Case not found" description={error} />
      </DashboardShell>
    );
  }

  if (!caseItem) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Support"
        title="Loading case…"
        description="Fetching case details and message history."
      >
        <SkeletonLoader lines={6} />
      </DashboardShell>
    );
  }

  const closed = isCaseClosed(caseItem);
  const canReply = !closed;
  const showAssign = !caseItem.assignee_user_id && !closed;
  const showEscalate = OPEN_STATUSES.has(caseItem.status);
  const showResolve = OPEN_STATUSES.has(caseItem.status);
  const showClose = caseItem.status !== "closed" && caseItem.status !== "archived";
  const showArchive =
    caseItem.status === "resolved" || caseItem.status === "closed";

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title={caseItem.subject}
      description={`${caseItem.case_number} · ${caseItem.category.replace(/_/g, " ")}`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={caseItem.status} />
          <Badge tone={priorityTone(caseItem.priority)}>
            {caseItem.priority.replace(/_/g, " ")}
          </Badge>
          <Link href="/support/cases">
            <Button variant="secondary" size="sm">
              All cases
            </Button>
          </Link>
        </div>
      }
    >
      <PageToolbar>
        <Link href="/support/cases">
          <Button size="sm" variant="ghost">
            Back to cases
          </Button>
        </Link>
      </PageToolbar>

      {closed ? (
        <Alert tone="warning" title="Case closed">
          Public replies are disabled. Internal notes can still be added for audit.
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

          {canReply ? (
            <Card className="space-y-4">
              <SectionHeader
                eyebrow="Reply"
                title="Public message"
                description="Sent to the requester and recorded on the case."
              />
              <SupportAIAssist
                ticketId={params.id}
                canDraftReply={canReply}
                onApplyReply={(draft) => setReplyBody(draft)}
                onApplyCategory={async (slug) => {
                  try {
                    const updated = await updateSupportCaseCategory(
                      params.id,
                      slug,
                    );
                    setCaseItem(updated);
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
                    const updated = await updateSupportCasePriority(
                      params.id,
                      priority,
                    );
                    setCaseItem(updated);
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
              <Textarea
                label="Message"
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                rows={4}
                placeholder="Write a reply the user can read…"
              />
              <Button
                disabled={replyBusy || !replyBody.trim()}
                onClick={() => void onReply()}
              >
                {replyBusy ? "Sending…" : "Send reply"}
              </Button>
            </Card>
          ) : (
            <Card className="space-y-4">
              <SectionHeader
                eyebrow="AI Assist"
                title="Ticket insights"
                description="Draft summaries and triage suggestions for staff review."
              />
              <SupportAIAssist
                ticketId={params.id}
                canDraftReply={false}
                onApplyCategory={async (slug) => {
                  try {
                    const updated = await updateSupportCaseCategory(
                      params.id,
                      slug,
                    );
                    setCaseItem(updated);
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
                    const updated = await updateSupportCasePriority(
                      params.id,
                      priority,
                    );
                    setCaseItem(updated);
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
            </Card>
          )}

          <Card className="space-y-4 border-l-4 border-l-accent">
            <SectionHeader
              eyebrow="Staff only"
              title="Internal notes"
              description="Not visible to the requester. Use for audit-friendly context."
            />
            {caseItem.internal_notes.length > 0 ? (
              <ul className="space-y-3">
                {caseItem.internal_notes.map((note) => (
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
                    <p className="whitespace-pre-wrap text-muted-foreground">{note.body}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No internal notes yet.</p>
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
          </Card>
        </div>

        <aside className="min-w-0 space-y-4">
          <Card className="space-y-3">
            <SectionHeader eyebrow="Summary" title="Case details" />
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Case number</dt>
                <dd className="font-bold text-foreground">{caseItem.case_number}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Status</dt>
                <dd>
                  <StatusBadge status={caseItem.status} />
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Priority</dt>
                <dd>
                  <Badge tone={priorityTone(caseItem.priority)}>
                    {caseItem.priority.replace(/_/g, " ")}
                  </Badge>
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Category</dt>
                <dd className="font-medium capitalize text-foreground">
                  {caseItem.category.replace(/_/g, " ")}
                </dd>
              </div>
              {caseItem.escalation_level ? (
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Escalation</dt>
                  <dd className="font-medium uppercase text-foreground">
                    {caseItem.escalation_level}
                  </dd>
                </div>
              ) : null}
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Created</dt>
                <dd className="text-foreground">{formatDateTime(caseItem.created_at)}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Updated</dt>
                <dd className="text-foreground">{formatDateTime(caseItem.updated_at)}</dd>
              </div>
            </dl>
          </Card>

          {(caseItem.related_order_id || caseItem.related_event_id) && (
            <Card className="space-y-3">
              <SectionHeader eyebrow="Links" title="Related records" />
              <dl className="space-y-2 text-sm">
                {caseItem.related_order_id ? (
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">Order</dt>
                    <dd>
                      <Link
                        href={`/dashboard/orders/${caseItem.related_order_id}`}
                        className="font-medium text-foreground underline-offset-2 hover:underline"
                      >
                        View order
                      </Link>
                    </dd>
                  </div>
                ) : null}
                {caseItem.related_event_id ? (
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">Event</dt>
                    <dd className="break-all font-mono text-xs text-foreground">
                      {caseItem.related_event_id}
                    </dd>
                  </div>
                ) : null}
              </dl>
            </Card>
          )}

          <Card className="space-y-4">
            <SectionHeader
              eyebrow="Actions"
              title="Lifecycle"
              description="Recorded for audit. Cases are archived, never deleted."
            />
            <div className="flex flex-wrap gap-2">
              {showAssign && user?.id ? (
                <ConfirmAction
                  label="Assign to me"
                  title="Assign this case to you?"
                  description="You become the assignee and the case moves to in progress if it was open."
                  confirmLabel="Assign"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Case assigned", () =>
                      assignSupportCase(params.id, user.id),
                    )
                  }
                />
              ) : null}

              {showEscalate ? (
                <ConfirmAction
                  label="Escalate"
                  title="Escalate this case?"
                  description="Sets status to escalated and records the escalation level."
                  confirmLabel="Escalate"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Case escalated", () =>
                      escalateSupportCase(
                        params.id,
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
                      hint="Added as an internal escalation note."
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
                  title="Mark case resolved?"
                  description="Use when the issue is fixed. The requester can still reply unless you close the case."
                  confirmLabel="Resolve"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Case resolved", () => resolveSupportCase(params.id))
                  }
                />
              ) : null}

              {showClose ? (
                <ConfirmAction
                  label="Close"
                  title="Close this case?"
                  description="Stops public replies. Use when no further action is needed."
                  confirmLabel="Close case"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Case closed", () => closeSupportCase(params.id))
                  }
                />
              ) : null}

              {showArchive ? (
                <ConfirmAction
                  label="Archive"
                  title="Archive this case?"
                  description="Removes the case from active queues. Archived cases cannot be reopened from this UI."
                  confirmLabel="Archive"
                  busy={actionBusy}
                  onConfirm={() =>
                    runAction("Case archived", () => archiveSupportCase(params.id))
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
