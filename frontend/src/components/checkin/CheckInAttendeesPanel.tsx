"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { Alert, Button, Input, StatusBadge } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchCheckIns,
  searchAttendees,
  type CheckInLog,
  type DeskAttendee,
} from "@/lib/checkin-api";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";

type AttendeeFilter = "all" | "pending" | "checked_in" | "vip" | "issues";

export function CheckInAttendeesPanel({
  eventId,
  online,
  busy,
  onCheckIn,
}: {
  eventId: string;
  online: boolean;
  busy: boolean;
  onCheckIn: (publicCode: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<AttendeeFilter>("all");
  const [searchRows, setSearchRows] = useState<DeskAttendee[]>([]);
  const [logs, setLogs] = useState<CheckInLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<DeskAttendee | null>(null);

  useEffect(() => {
    let active = true;
    void fetchCheckIns(eventId)
      .then((items) => {
        if (active) setLogs(items);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [eventId]);

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    if (!online) {
      setError("Guest search needs a connection.");
      return;
    }
    setError(null);
    try {
      setSearchRows(await searchAttendees(eventId, query.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed");
    }
  }

  const list = searchRows.length > 0 ? searchRows : [];

  const filtered = useMemo(() => {
    return list.filter((row) => {
      if (filter === "all") return true;
      if (filter === "pending") return row.status !== "checked_in";
      if (filter === "checked_in") return row.status === "checked_in";
      if (filter === "vip") return /vip/i.test(row.ticket_type_name);
      if (filter === "issues") return row.status !== "active" && row.status !== "checked_in";
      return true;
    });
  }, [list, filter]);

  const filters: { id: AttendeeFilter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "pending", label: "Not checked in" },
    { id: "checked_in", label: "Checked in" },
    { id: "vip", label: "VIP" },
    { id: "issues", label: "Issues" },
  ];

  return (
    <div className="space-y-4">
      <form className="flex flex-col gap-2 sm:flex-row sm:items-end" onSubmit={onSearch}>
        <Input
          label="Search guests"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Name or ticket code"
          className="min-w-0 flex-1"
        />
        <Button type="submit" disabled={!online} className="w-full sm:w-auto">
          Search
        </Button>
      </form>
      <p className="text-xs text-muted-foreground">
        Search by name or public ticket code. Email and phone are not shown at the door desk.
      </p>

      <div className="flex flex-wrap gap-1.5">
        {filters.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-bold",
              filter === f.id
                ? "bg-accent text-accent-foreground"
                : "bg-muted text-muted-foreground",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error ? (
        <Alert tone="danger" title="Search">
          {error}
        </Alert>
      ) : null}

      <ul className="space-y-2">
        {filtered.map((row) => (
          <li
            key={row.public_code}
            className="rounded-[var(--radius-md)] border border-border bg-surface-elevated p-3"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-foreground">{row.holder_name}</p>
                  <StatusBadge status={row.status} />
                </div>
                <p className="text-sm text-muted-foreground">
                  {row.ticket_type_name} · {row.public_code}
                </p>
                {row.checked_in_at ? (
                  <p className="text-xs text-muted-foreground">
                    Checked in {formatDateTime(row.checked_in_at)}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={() => setSelected(row)}>
                  View ticket
                </Button>
                <Button
                  size="sm"
                  disabled={busy || row.status === "checked_in"}
                  onClick={() => onCheckIn(row.public_code)}
                >
                  Check in
                </Button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {query.trim() && filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No matches.</p>
      ) : null}

      {!query.trim() && logs.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          {logs.length} check-in log entries on file — search to find a guest.
        </p>
      ) : null}

      {selected ? (
        <Alert tone="info" title={selected.holder_name}>
          <p className="text-sm">
            {selected.ticket_type_name} ·{" "}
            <span className="font-mono">{selected.public_code}</span>
          </p>
          <Button size="sm" variant="ghost" className="mt-2" onClick={() => setSelected(null)}>
            Close
          </Button>
        </Alert>
      ) : null}
    </div>
  );
}
