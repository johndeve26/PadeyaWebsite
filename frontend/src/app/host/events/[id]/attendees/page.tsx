"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  DataTable,
  Input,
  SectionHeader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  assignEventStaff,
  fetchCheckIns,
  fetchEventStaff,
  searchAttendees,
  unassignEventStaff,
  type CheckInLog,
  type DeskAttendee,
  type StaffAssignment,
} from "@/lib/checkin-api";

export default function HostAttendeesPage() {
  const params = useParams<{ id: string }>();
  const [query, setQuery] = useState("");
  const [tickets, setTickets] = useState<DeskAttendee[]>([]);
  const [logs, setLogs] = useState<CheckInLog[]>([]);
  const [staff, setStaff] = useState<StaffAssignment[]>([]);
  const [staffEmail, setStaffEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadStaff() {
    setStaff(await fetchEventStaff(params.id));
  }

  useEffect(() => {
    let active = true;
    void fetchCheckIns(params.id)
      .then((items) => {
        if (active) setLogs(items);
      })
      .catch(() => undefined);
    void fetchEventStaff(params.id)
      .then((items) => {
        if (active) setStaff(items);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setTickets(await searchAttendees(params.id, query));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed");
    }
  }

  async function onAssign(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      await assignEventStaff(params.id, staffEmail);
      setMessage(`Assigned ${staffEmail} as scanner staff.`);
      setStaffEmail("");
      await loadStaff();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Assignment failed");
    }
  }

  async function onUnassign(assignmentId: string, label: string) {
    setMessage(null);
    setError(null);
    try {
      await unassignEventStaff(params.id, assignmentId);
      setMessage(`Removed ${label} from door staff.`);
      await loadStaff();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unassign failed");
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Attendees"
        title="Guest list & door team"
        description="Search ticket holders, assign scanner staff, and review recent check-in activity."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={`/host/events/${params.id}/check-in`}>
              <Button size="sm">Open scanner</Button>
            </Link>
            <Link href={`/host/events/${params.id}/check-in/analytics`}>
              <Button size="sm" variant="secondary">
                Door stats
              </Button>
            </Link>
          </div>
        }
      >
        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">{logs.length} check-in logs</Badge>
          {tickets.length > 0 ? (
            <Badge tone="accent">{tickets.length} search results</Badge>
          ) : null}
        </div>

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}
        {message ? (
          <Alert tone="success" title="Staff assigned">
            {message}
          </Alert>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="space-y-4">
            <SectionHeader
              eyebrow="Door"
              title="Search attendees"
              description="Find guests by name or ticket public code (desk-minimal — no email)."
            />
            <form
              className="flex flex-col gap-3 sm:flex-row sm:items-end"
              onSubmit={onSearch}
            >
              <Input
                label="Query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Name or PDY-…"
              />
              <Button type="submit" className="w-full sm:w-auto">
                Search
              </Button>
            </form>
            <DataTable
              rows={tickets}
              rowKey={(t) => t.id}
              emptyTitle="No results"
              emptyDescription="Search by name or public code."
              columns={[
                {
                  key: "name",
                  header: "Holder",
                  cell: (t) => <span className="font-semibold">{t.holder_name}</span>,
                },
                { key: "type", header: "Type", cell: (t) => t.ticket_type_name },
                {
                  key: "code",
                  header: "Code",
                  cell: (t) => (
                    <span className="font-mono text-xs">{t.public_code}</span>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (t) => <StatusBadge status={t.status} />,
                },
              ]}
            />
          </Card>

          <Card className="space-y-4">
            <SectionHeader
              eyebrow="Door team"
              title="Assign scanner staff"
              description="Staff must already have a Pàdéyá account. They get host_staff for this event only."
            />
            <form className="space-y-3" onSubmit={onAssign}>
              <Input
                label="Staff email"
                type="text"
                inputMode="email"
                required
                value={staffEmail}
                onChange={(e) => setStaffEmail(e.target.value)}
                placeholder="scanner@example.com"
              />
              <Button type="submit" className="w-full sm:w-auto">
                Assign staff
              </Button>
            </form>
            {staff.length > 0 ? (
              <ul className="divide-y divide-border rounded-[var(--radius-md)] border border-border">
                {staff.map((row) => {
                  const label = row.user_name || row.user_email || "Staff";
                  return (
                    <li
                      key={row.id}
                      className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-foreground">
                          {label}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          {row.user_email}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => void onUnassign(row.id, label)}
                      >
                        Unassign
                      </Button>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </Card>
        </div>

        <section className="mt-8 space-y-4">
          <SectionHeader
            eyebrow="Activity"
            title="Recent check-in logs"
            description="Latest 20 scan outcomes at the door."
          />
          <DataTable
            rows={logs.slice(0, 20)}
            rowKey={(log) => log.id}
            emptyTitle="No check-ins yet"
            emptyDescription="Scan activity will appear here once the door opens."
            columns={[
              {
                key: "when",
                header: "When",
                cell: (log) => formatDateTime(log.created_at),
              },
              {
                key: "out",
                header: "Outcome",
                cell: (log) => <StatusBadge status={log.outcome} />,
              },
              {
                key: "who",
                header: "Attendee",
                cell: (log) => log.holder_name ?? log.ticket_public_code ?? "—",
              },
              {
                key: "scan",
                header: "Scanner",
                cell: (log) => log.scanner_name ?? "—",
              },
            ]}
          />
        </section>
      </DashboardShell>
    </RequireHost>
  );
}
