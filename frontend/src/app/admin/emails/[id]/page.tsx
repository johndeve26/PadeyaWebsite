"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Button, Card, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminEmail, resendAdminEmail, type EmailEvent } from "@/lib/email-api";
import { formatDateTime } from "@/lib/format";

export default function AdminEmailDetailPage() {
  const params = useParams();
  const id = String(params.id || "");
  const toast = useToast();
  const [row, setRow] = useState<EmailEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    let active = true;
    void (async () => {
      try {
        const data = await fetchAdminEmail(id);
        if (active) setRow(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [id]);

  async function onResend() {
    setBusy(true);
    try {
      const result = await resendAdminEmail(id);
      toast.push({ tone: "success", title: `Resend → ${result.status}` });
      setRow(await fetchAdminEmail(id));
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Resend failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Email event"
      description="Outbox delivery record for Pàdéyá transactional email."
      actions={
        <Link href="/admin/emails">
          <Button variant="secondary">Back</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {!row ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <Card className="max-w-2xl space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="neutral">{row.status}</Badge>
            <span className="font-bold">{row.template}</span>
          </div>
          <dl className="grid gap-2 text-sm">
            <div>
              <dt className="text-muted-foreground">Recipient</dt>
              <dd>{row.recipient_email}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Subject</dt>
              <dd>{row.subject}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Attempts</dt>
              <dd>{row.attempts}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Provider</dt>
              <dd>
                {row.provider || "—"}
                {row.provider_message_id ? ` · ${row.provider_message_id}` : ""}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Sent</dt>
              <dd>{row.sent_at ? formatDateTime(row.sent_at) : "—"}</dd>
            </div>
            {row.error_message ? (
              <div>
                <dt className="text-muted-foreground">Error</dt>
                <dd>{row.error_message}</dd>
              </div>
            ) : null}
            {row.body_text ? (
              <div>
                <dt className="text-muted-foreground">Body preview (dev)</dt>
                <dd>
                  <pre className="mt-1 whitespace-pre-wrap rounded-md bg-surface-muted p-3 text-xs">
                    {row.body_text}
                  </pre>
                </dd>
              </div>
            ) : null}
          </dl>
          <Button disabled={busy} onClick={() => void onResend()}>
            {busy ? "Resending…" : "Resend"}
          </Button>
        </Card>
      )}
    </DashboardShell>
  );
}
