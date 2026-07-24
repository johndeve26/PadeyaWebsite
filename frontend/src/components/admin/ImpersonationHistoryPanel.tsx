"use client";

import { Badge, Card, SectionHeader } from "@/components/ui";
import type { ImpersonationHistoryItem } from "@/lib/auth/types";
import { cn } from "@/lib/cn";

function formatWhen(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function statusTone(
  status: string,
): "success" | "warning" | "danger" | "neutral" {
  switch (status) {
    case "active":
      return "warning";
    case "ended":
      return "success";
    case "expired":
    case "revoked":
      return "danger";
    default:
      return "neutral";
  }
}

export function ImpersonationHistoryPanel({
  rows,
  loading,
  className,
}: {
  rows: ImpersonationHistoryItem[];
  loading?: boolean;
  className?: string;
}) {
  return (
    <Card className={cn("space-y-4", className)}>
      <SectionHeader
        eyebrow="Audit"
        title="Impersonation history"
        description="Past and active sessions for this account."
      />

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading history…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No impersonation sessions recorded yet.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                <th className="py-2 pr-3 font-bold">Started by</th>
                <th className="py-2 pr-3 font-bold">Reason</th>
                <th className="py-2 pr-3 font-bold">Started</th>
                <th className="py-2 pr-3 font-bold">Ended</th>
                <th className="py-2 font-bold">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-border/70 align-top last:border-b-0"
                >
                  <td className="py-3 pr-3">
                    <div className="font-semibold text-foreground">
                      {row.started_by}
                    </div>
                    {row.started_by_email ? (
                      <div className="text-xs text-muted-foreground">
                        {row.started_by_email}
                      </div>
                    ) : null}
                  </td>
                  <td className="max-w-[16rem] py-3 pr-3">
                    <p className="line-clamp-3 text-foreground">{row.reason}</p>
                    {row.support_ticket_id ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Ticket: {row.support_ticket_id}
                      </p>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap py-3 pr-3 text-muted-foreground">
                    {formatWhen(row.started_at)}
                  </td>
                  <td className="whitespace-nowrap py-3 pr-3 text-muted-foreground">
                    {formatWhen(row.ended_at)}
                  </td>
                  <td className="py-3">
                    <Badge tone={statusTone(row.status)}>{row.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
