"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
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
  Input,
  SectionHeader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  assignEventTable,
  cancelEventTable,
  createEventTable,
  fetchEventTables,
  fetchEventTransfers,
} from "@/lib/advanced-tickets-api";
import type { TableReservation, TicketTransfer } from "@/lib/types/advanced-tickets";

export default function HostEventTablesPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [tables, setTables] = useState<TableReservation[]>([]);
  const [transfers, setTransfers] = useState<TicketTransfer[]>([]);
  const [label, setLabel] = useState("");
  const [capacity, setCapacity] = useState("4");
  const [ticketId, setTicketId] = useState("");
  const [assignId, setAssignId] = useState<string | null>(null);
  const [seatLabel, setSeatLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busyTableId, setBusyTableId] = useState<string | null>(null);

  async function reload() {
    const [t, tr] = await Promise.all([
      fetchEventTables(params.id),
      fetchEventTransfers(params.id),
    ]);
    setTables(t);
    setTransfers(tr);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [t, tr] = await Promise.all([
          fetchEventTables(params.id),
          fetchEventTransfers(params.id),
        ]);
        if (!active) return;
        setTables(t);
        setTransfers(tr);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onCreate() {
    setError(null);
    try {
      await createEventTable(params.id, {
        table_label: label,
        capacity: Number(capacity) || 1,
      });
      setLabel("");
      setNote("Table created.");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    }
  }

  async function onAssign() {
    if (!assignId) return;
    setError(null);
    try {
      await assignEventTable(assignId, {
        ticket_id: ticketId || undefined,
        seat_label: seatLabel || undefined,
      });
      setNote("Seat assignment saved (placeholder).");
      setTicketId("");
      setSeatLabel("");
      setAssignId(null);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Assign failed");
    }
  }

  async function onCancelTable(tableId: string, tableLabel: string) {
    setBusyTableId(tableId);
    setError(null);
    try {
      await cancelEventTable(tableId);
      toast.push({
        title: "Table cancelled",
        description: `${tableLabel} is no longer active.`,
        tone: "success",
      });
      if (assignId === tableId) setAssignId(null);
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Cancel failed";
      setError(detail);
      toast.push({ title: "Cancel failed", description: detail, tone: "danger" });
    } finally {
      setBusyTableId(null);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Tables"
        title="Table & seat management"
        description="Manage table reservations and seat placeholders. Assignments do not change payment or inventory."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={`/host/events/${params.id}`}>
              <Button size="sm" variant="ghost">
                Back to event
              </Button>
            </Link>
            <Link href={`/host/events/${params.id}/offline-check-in`}>
              <Button size="sm" variant="secondary">
                Offline check-in
              </Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}
        {note ? (
          <Alert tone="success" title="Saved">
            {note}
          </Alert>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">{tables.length} tables</Badge>
          <Badge tone="neutral">{transfers.length} transfers</Badge>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <Card className="space-y-4">
            <SectionHeader
              title="Add table"
              description="Create a new table reservation for VIP or seated sections."
            />
            <Input
              label="Table label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="VIP-A"
            />
            <Input
              label="Capacity"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              inputMode="numeric"
            />
            <Button disabled={!label} onClick={() => void onCreate()}>
              Create table
            </Button>
          </Card>

          <section className="space-y-4">
            <SectionHeader
              eyebrow="Floor plan"
              title="Reservations"
              description="Assign seats to ticket holders at each table."
            />
            {tables.length === 0 ? (
              <EmptyState
                title="No tables yet"
                description="Add your first table to start assigning seats."
              />
            ) : (
              <div className="space-y-3">
                {tables.map((row) => (
                  <Card key={row.id} className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-lg font-extrabold text-foreground">
                        {row.table_label}
                      </p>
                      <StatusBadge status={row.status} />
                      <span className="text-sm text-muted-foreground">
                        Capacity {row.capacity}
                        {row.seat_label ? ` · Seat ${row.seat_label}` : ""}
                      </span>
                    </div>
                    {row.primary_ticket_id ? (
                      <p className="text-sm text-muted-foreground">
                        Ticket{" "}
                        <span className="font-mono">{row.primary_ticket_id}</span>
                      </p>
                    ) : null}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant={assignId === row.id ? "dark" : "secondary"}
                        onClick={() =>
                          setAssignId(assignId === row.id ? null : row.id)
                        }
                      >
                        {assignId === row.id ? "Close" : "Assign seat"}
                      </Button>
                      {row.status !== "cancelled" ? (
                        <ConfirmAction
                          label="Cancel table"
                          title="Cancel this table?"
                          description={`Cancel ${row.table_label}. Existing seat assignments will no longer be active.`}
                          confirmLabel="Cancel table"
                          tone="danger"
                          disabled={busyTableId === row.id}
                          busy={busyTableId === row.id}
                          onConfirm={() => onCancelTable(row.id, row.table_label)}
                        />
                      ) : null}
                    </div>
                    {assignId === row.id ? (
                      <div className="space-y-3 border-t border-border pt-4">
                        <Input
                          label="Ticket ID"
                          value={ticketId}
                          onChange={(e) => setTicketId(e.target.value)}
                        />
                        <Input
                          label="Seat label"
                          value={seatLabel}
                          onChange={(e) => setSeatLabel(e.target.value)}
                          placeholder="A1"
                        />
                        <Button size="sm" onClick={() => void onAssign()}>
                          Save assignment
                        </Button>
                      </div>
                    ) : null}
                  </Card>
                ))}
              </div>
            )}
          </section>
        </div>

        <section className="mt-10 space-y-4">
          <SectionHeader
            eyebrow="History"
            title="Transfer history"
            description="Ticket transfers between guests for this event."
          />
          {transfers.length === 0 ? (
            <EmptyState
              title="No transfers"
              description="Ticket transfers will appear here when guests reassign tickets."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {transfers.map((row) => (
                <Card key={row.id} className="space-y-1">
                  <p className="text-sm font-semibold text-foreground">
                    {row.from_email} → {row.to_email}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDateTime(row.created_at)}
                  </p>
                </Card>
              ))}
            </div>
          )}
        </section>
      </DashboardShell>
    </RequireHost>
  );
}
