"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { CancelTicketButton } from "@/components/tickets/CancelTicketButton";
import {
  Alert,
  Button,
  DataTable,
  FilterBar,
  PageToolbar,
  SearchBar,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminTickets,
  fetchAdminTransfers,
} from "@/lib/advanced-tickets-api";
import { formatDateTime } from "@/lib/format";
import type { TicketTransfer } from "@/lib/types/advanced-tickets";
import type { Ticket } from "@/lib/types/commerce";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "checked_in", label: "Checked in" },
  { value: "cancelled", label: "Cancelled" },
  { value: "transferred", label: "Transferred" },
];

export default function AdminTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [transfers, setTransfers] = useState<TicketTransfer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  async function reload() {
    const [t, tr] = await Promise.all([
      fetchAdminTickets(),
      fetchAdminTransfers(),
    ]);
    setTickets(t);
    setTransfers(tr);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [t, tr] = await Promise.all([
          fetchAdminTickets(),
          fetchAdminTransfers(),
        ]);
        if (!active) return;
        setTickets(t);
        setTransfers(tr);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
          setTickets([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filteredTickets = useMemo(() => {
    if (!tickets) return [];
    const q = search.trim().toLowerCase();
    return tickets.filter((t) => {
      if (statusFilter !== "all" && t.status !== statusFilter) return false;
      if (!q) return true;
      return (
        t.public_code.toLowerCase().includes(q) ||
        t.holder_email.toLowerCase().includes(q) ||
        (t.event_title ?? t.event_id).toLowerCase().includes(q) ||
        t.ticket_type_name.toLowerCase().includes(q)
      );
    });
  }, [tickets, statusFilter, search]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Tickets"
      description="Platform ticket overview, transfers, and cancellation. Does not alter payment settlements."
    >
      <PageToolbar>
        <Link href="/admin">
          <Button size="sm" variant="ghost">
            Admin home
          </Button>
        </Link>
      </PageToolbar>

      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}
      {success ? (
        <Alert tone="success" title="Updated">
          {success}
        </Alert>
      ) : null}

      {tickets ? (
        <>
          <section className="space-y-4">
            <SectionHeader title="Recent tickets" />

            <FilterBar>
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
              <SearchBar
                placeholder="Code, holder, event…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </FilterBar>

            <DataTable
              rows={filteredTickets}
              rowKey={(t) => t.id}
              emptyTitle="No tickets found"
              emptyDescription={
                search || statusFilter !== "all"
                  ? "Try adjusting your search or status filter."
                  : "Issued tickets will appear here."
              }
              columns={[
                {
                  key: "code",
                  header: "Code",
                  primary: true,
                  cell: (t) => (
                    <span className="font-mono font-bold">{t.public_code}</span>
                  ),
                },
                {
                  key: "event",
                  header: "Event",
                  cell: (t) => t.event_title ?? t.event_id,
                },
                {
                  key: "type",
                  header: "Type",
                  cell: (t) => t.ticket_type_name,
                },
                {
                  key: "holder",
                  header: "Holder",
                  cell: (t) => (
                    <div className="min-w-0">
                      <p className="font-semibold">{t.holder_name}</p>
                      <p className="text-sm text-muted-foreground">{t.holder_email}</p>
                    </div>
                  ),
                },
                {
                  key: "table",
                  header: "Table",
                  cell: (t) => t.table_label ?? "—",
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (t) => <StatusBadge status={t.status} />,
                },
                {
                  key: "actions",
                  header: "",
                  cell: (t) =>
                    t.status === "active" || t.status === "checked_in" ? (
                      <CancelTicketButton
                        ticketId={t.id}
                        label="Cancel"
                        reason="Admin cancellation"
                        onCancelled={async () => {
                          setError(null);
                          setSuccess(
                            `Ticket ${t.public_code} cancelled permanently; QR revoked.`,
                          );
                          await reload();
                        }}
                        onError={(message) => {
                          setSuccess(null);
                          setError(message);
                        }}
                      />
                    ) : null,
                },
              ]}
            />
          </section>

          <section className="space-y-4">
            <SectionHeader
              title="Transfer audit"
              description="Immutable record of ticket transfers between holders."
            />

            <DataTable
              rows={transfers}
              rowKey={(row) => row.id}
              emptyTitle="No transfers recorded"
              emptyDescription="Ticket transfer history appears here for audit."
              columns={[
                {
                  key: "ticket",
                  header: "Ticket",
                  primary: true,
                  cell: (row) => (
                    <span className="font-mono text-sm">{row.ticket_id}</span>
                  ),
                },
                {
                  key: "from",
                  header: "From",
                  cell: (row) => row.from_email,
                },
                {
                  key: "to",
                  header: "To",
                  cell: (row) => row.to_email,
                },
                {
                  key: "when",
                  header: "When",
                  cell: (row) => formatDateTime(row.created_at),
                },
              ]}
            />
          </section>
        </>
      ) : null}

      {tickets == null && !error ? <SkeletonLoader lines={5} /> : null}
    </DashboardShell>
  );
}
