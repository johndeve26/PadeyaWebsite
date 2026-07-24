"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Button, Card, EmptyState } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminEmails, type EmailEvent } from "@/lib/email-api";
import { formatDateTime } from "@/lib/format";

export default function AdminEmailsPage() {
  const [items, setItems] = useState<EmailEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchAdminEmails({
          status: status || undefined,
          limit: 100,
        });
        if (!active) return;
        setItems(data.items);
        setTotal(data.total);
        setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load emails");
          setItems([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [status]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Email outbox"
      description="Queued transactional emails. Bodies are hidden in production unless configured for preview."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/emails/templates">
            <Button size="sm">Platform templates</Button>
          </Link>
          <Link href="/admin/emails/settings">
            <Button size="sm" variant="secondary">
              Email settings
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

      <div className="mb-4 flex flex-wrap gap-2">
        {["", "pending", "sent", "failed", "skipped"].map((s) => (
          <Button
            key={s || "all"}
            size="sm"
            variant={status === s ? "secondary" : "ghost"}
            onClick={() => setStatus(s)}
          >
            {s || "all"}
          </Button>
        ))}
        <span className="self-center text-sm text-muted-foreground">{total} total</span>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No email events"
          description="Events appear after verified payments and other product triggers."
        />
      ) : (
        <div className="space-y-3">
          {items.map((row) => (
            <Card key={row.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral" size="sm">
                    {row.status}
                  </Badge>
                  <span className="font-semibold">{row.template}</span>
                </div>
                <p className="mt-1 truncate text-sm text-muted-foreground">
                  {row.recipient_email} · {row.subject}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDateTime(row.created_at)}
                  {row.error_message ? ` · ${row.error_message}` : ""}
                </p>
              </div>
              <Link href={`/admin/emails/${row.id}`}>
                <Button size="sm" variant="secondary">
                  Details
                </Button>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </DashboardShell>
  );
}
