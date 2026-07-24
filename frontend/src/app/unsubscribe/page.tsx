"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { unsubscribeWithToken } from "@/lib/email-api";

function UnsubscribeForm() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onUnsubscribe() {
    if (!token) {
      setError("Missing unsubscribe token.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await unsubscribeWithToken(token, true);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not unsubscribe");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-lg flex-col justify-center px-4 py-16">
      <Card className="space-y-4">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Pàdéyá
        </p>
        <h1 className="text-2xl font-extrabold text-foreground">
          Unsubscribe from marketing
        </h1>
        <p className="text-sm text-muted-foreground">
          You’ll stop receiving marketing and post-event drop emails. Security and
          purchase confirmation emails will continue.
        </p>
        {error ? (
          <Alert tone="danger" title="Could not update">
            {error}
          </Alert>
        ) : null}
        {done ? (
          <Alert tone="success" title="You’re unsubscribed">
            Marketing emails are off. Manage other preferences anytime in Settings.
          </Alert>
        ) : (
          <Button size="lg" disabled={busy || !token} onClick={() => void onUnsubscribe()}>
            {busy ? "Updating…" : "Unsubscribe from marketing"}
          </Button>
        )}
        <a
          className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
          href={token ? `/email/preferences?token=${encodeURIComponent(token)}` : "/dashboard/settings/notifications"}
        >
          Manage all email preferences
        </a>
      </Card>
    </main>
  );
}

export default function UnsubscribePage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-muted-foreground">Loading…</p>}>
      <UnsubscribeForm />
    </Suspense>
  );
}
