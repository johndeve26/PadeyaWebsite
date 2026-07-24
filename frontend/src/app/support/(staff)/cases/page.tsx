"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  PageToolbar,
  Select,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchStaffSupportCases } from "@/lib/support-api";
import type { SupportCase } from "@/lib/types/support";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "waiting_on_user", label: "Waiting on user" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

function priorityTone(priority: string): "neutral" | "warning" | "danger" {
  const key = priority.toLowerCase();
  if (key === "urgent") return "danger";
  if (key === "high") return "warning";
  return "neutral";
}

export default function SupportCasesPage() {
  const [rows, setRows] = useState<SupportCase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    const status = statusFilter === "all" ? undefined : statusFilter;
    const data = await fetchStaffSupportCases(status);
    setRows(data);
  }, [statusFilter]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load support cases",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((c) => {
      const haystack = [c.subject, c.case_number].join(" ").toLowerCase();
      return haystack.includes(q);
    });
  }, [rows, search]);

  const openCount = useMemo(
    () =>
      (rows ?? []).filter((c) =>
        ["open", "in_progress", "waiting_on_user", "escalated"].includes(c.status),
      ).length,
    [rows],
  );

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title="Support cases"
      description="Assign, reply, escalate, and resolve product support cases on Pàdéyá."
      actions={
        <Link href="/support/cases/new">
          <Button size="lg">New case</Button>
        </Link>
      }
    >
      <PageToolbar>
        <Link href="/support/desk">
          <Button size="sm" variant="ghost">
            Support home
          </Button>
        </Link>
      </PageToolbar>

      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {rows ? (
        <>
          <FilterBar
            trailing={
              <span className="text-sm text-muted-foreground">
                {filtered.length} case{filtered.length === 1 ? "" : "s"}
                {openCount > 0 ? ` · ${openCount} open` : ""}
              </span>
            }
          >
            <Input
              label="Search"
              placeholder="Subject or case number…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Select
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </FilterBar>

          {filtered.length === 0 ? (
            <EmptyState
              title="No support cases"
              description={
                search || statusFilter !== "all"
                  ? "No cases match your filters. Try a different search or status."
                  : "When cases are created, they appear here for triage."
              }
              action={
                <Link href="/support/cases/new">
                  <Button>Create case</Button>
                </Link>
              }
            />
          ) : (
            <DataTable
              rows={filtered}
              rowKey={(c) => c.id}
              emptyTitle="No support cases"
              emptyDescription="When cases are created, they appear here."
              columns={[
                {
                  key: "case_number",
                  header: "Case",
                  primary: true,
                  cell: (c) => (
                    <Link
                      href={`/support/cases/${c.id}`}
                      className="font-bold text-foreground underline-offset-2 hover:underline"
                    >
                      {c.case_number}
                    </Link>
                  ),
                },
                {
                  key: "subject",
                  header: "Subject",
                  cell: (c) => (
                    <Link
                      href={`/support/cases/${c.id}`}
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
                      {c.priority.replace(/_/g, " ")}
                    </Badge>
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
                  href={`/support/cases/${c.id}`}
                  className="block rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] transition-colors hover:bg-surface-muted/80 dark:bg-surface-elevated"
                >
                  <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 space-y-1">
                      <p className="font-extrabold text-foreground">{c.case_number}</p>
                      <p className="text-sm text-foreground">{c.subject}</p>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <Badge tone={priorityTone(c.priority)}>
                      {c.priority.replace(/_/g, " ")}
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

      {rows == null && !error ? <SkeletonLoader lines={5} /> : null}
    </DashboardShell>
  );
}
