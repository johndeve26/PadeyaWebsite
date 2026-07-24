"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { AdminAISummaryPanel } from "@/components/admin/AdminAISummaryPanel";
import {
  Alert,
  Badge,
  Button,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  Select,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchAdminSupportTickets,
  fetchSupportMeta,
  supportTicketNumber,
} from "@/lib/support-api";
import {
  FALLBACK_SUPPORT_CATEGORIES,
  OPEN_SUPPORT_STATUSES,
  SUPPORT_CONTEXT_OPTIONS,
  SUPPORT_PRIORITY_OPTIONS,
  SUPPORT_STATUS_OPTIONS,
  formatSupportLabel,
  priorityTone,
} from "@/lib/support-ui";
import type { SupportCase, SupportCategoryOption } from "@/lib/types/support";

export default function AdminSupportQueuePage() {
  const [rows, setRows] = useState<SupportCase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("all");
  const [priority, setPriority] = useState("all");
  const [category, setCategory] = useState("all");
  const [context, setContext] = useState("all");
  const [q, setQ] = useState("");
  const [categories, setCategories] = useState<SupportCategoryOption[]>([
    ...FALLBACK_SUPPORT_CATEGORIES,
  ]);

  const load = useCallback(async () => {
    try {
      const data = await fetchAdminSupportTickets({
        status: status === "all" ? undefined : status,
        priority: priority === "all" ? undefined : priority,
        category: category === "all" ? undefined : category,
        requester_context: context === "all" ? undefined : context,
      });
      setRows(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to load support queue",
      );
      setRows([]);
    }
  }, [status, priority, category, context]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate queue
    void load();
  }, [load]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const meta = await fetchSupportMeta();
        if (active && meta.categories?.length) setCategories(meta.categories);
      } catch {
        // keep fallbacks
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((c) => {
      const hay = [
        c.subject,
        c.case_number,
        c.ticket_number,
        c.requester_email,
        c.requester_name,
        c.category,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    });
  }, [rows, q]);

  const openCount = useMemo(
    () => filtered.filter((c) => OPEN_SUPPORT_STATUSES.has(c.status)).length,
    [filtered],
  );

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Support queue"
      description="Triage tickets from fans, hosts, and visitors. Finance write actions stay with finance roles."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/support/settings">
            <Button variant="secondary">Settings</Button>
          </Link>
          <Link href="/admin/support/ai-summary">
            <Button variant="secondary">AI summary</Button>
          </Link>
          <Link href="/support/refunds">
            <Button variant="secondary">Refunds</Button>
          </Link>
          <Link href="/support/cases">
            <Button>Agent cases</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Queue unavailable">
          {error}
        </Alert>
      ) : null}

      <AdminAISummaryPanel
        feature="admin.support.queue_summary"
        title="Support queue AI summary"
        generateLabel="Summarize queue"
        links={[
          { href: "/support/refunds", label: "Refunds" },
          { href: "/admin/support/ai-summary", label: "Legacy AI page" },
        ]}
      />

      {rows == null && !error ? <SkeletonLoader lines={5} /> : null}

      {rows ? (
        <>
          <FilterBar
            trailing={
              <span className="text-sm text-muted-foreground">
                {filtered.length} ticket{filtered.length === 1 ? "" : "s"}
                {openCount > 0 ? ` · ${openCount} open` : ""}
              </span>
            }
          >
            <Input
              label="Search"
              placeholder="Subject, number, email…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {SUPPORT_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Select
              label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              {SUPPORT_PRIORITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Select
              label="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="all">All categories</option>
              {categories.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Select
              label="Context"
              value={context}
              onChange={(e) => setContext(e.target.value)}
            >
              {SUPPORT_CONTEXT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </FilterBar>

          {filtered.length === 0 ? (
            <EmptyState
              title="No tickets match"
              description="Try clearing filters or check the agent case desk."
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setStatus("all");
                    setPriority("all");
                    setCategory("all");
                    setContext("all");
                    setQ("");
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <DataTable
              rows={filtered}
              rowKey={(c) => c.id}
              emptyTitle="No tickets"
              emptyDescription="Tickets will appear here as they arrive."
              columns={[
                {
                  key: "case_number",
                  header: "Ticket",
                  primary: true,
                  cell: (c) => (
                    <Link
                      href={`/admin/support/${c.id}`}
                      className="font-bold text-foreground underline-offset-2 hover:underline"
                    >
                      {supportTicketNumber(c)}
                    </Link>
                  ),
                },
                {
                  key: "subject",
                  header: "Subject",
                  cell: (c) => (
                    <Link
                      href={`/admin/support/${c.id}`}
                      className="text-foreground underline-offset-2 hover:underline"
                    >
                      {c.subject}
                    </Link>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (c) => <StatusBadge status={c.status} />,
                },
                {
                  key: "priority",
                  header: "Priority",
                  cell: (c) => (
                    <Badge tone={priorityTone(c.priority)}>
                      {formatSupportLabel(c.priority)}
                    </Badge>
                  ),
                },
                {
                  key: "category",
                  header: "Category",
                  cell: (c) => (
                    <span className="capitalize text-muted-foreground">
                      {formatSupportLabel(c.category)}
                    </span>
                  ),
                },
                {
                  key: "updated_at",
                  header: "Updated",
                  cell: (c) => (
                    <span className="whitespace-nowrap text-muted-foreground">
                      {formatDateTime(c.updated_at)}
                    </span>
                  ),
                },
              ]}
              mobileCard={(c) => (
                <Link
                  href={`/admin/support/${c.id}`}
                  className="block rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] transition-colors hover:bg-surface-muted/80 dark:bg-surface-elevated"
                >
                  <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 space-y-1">
                      <p className="font-extrabold text-foreground">
                        {supportTicketNumber(c)}
                      </p>
                      <p className="text-sm text-foreground">{c.subject}</p>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <Badge tone={priorityTone(c.priority)}>
                      {formatSupportLabel(c.priority)}
                    </Badge>
                    <span className="text-muted-foreground">
                      {formatDateTime(c.updated_at)}
                    </span>
                  </div>
                </Link>
              )}
            />
          )}
        </>
      ) : null}
    </DashboardShell>
  );
}
