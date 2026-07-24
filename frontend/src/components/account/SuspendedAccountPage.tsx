"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Button,
  Container,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

type SuspensionPublic = {
  id: string;
  status: string;
  reason_category: string;
  reason_category_label: string;
  starts_at: string;
  ends_at: string | null;
  duration_label: string;
};

type SuspensionPayload = {
  suspension: SuspensionPublic | null;
  pending_appeal: { id: string; status: string; created_at: string } | null;
};

/**
 * Full-page suspended account experience: public category/duration/date,
 * Appeal + Logout. Never shows internal admin notes.
 */
export function SuspendedAccountPage() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const [payload, setPayload] = useState<SuspensionPayload | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiRequest<SuspensionPayload>("/me/suspension");
      setPayload(data);
      if (data.pending_appeal) setSubmitted(true);
    } catch {
      const fromUser = user?.suspension ?? undefined;
      setPayload({
        suspension: fromUser || null,
        pending_appeal: null,
      });
    }
  }, [user]);

  useEffect(() => {
    // Intentional mount fetch for public suspension details.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load() updates suspension payload
    void load();
  }, [load]);

  const suspension =
    payload?.suspension || user?.suspension || null;

  async function onAppeal(e: React.FormEvent) {
    e.preventDefault();
    if (message.trim().length < 10 || busy) return;
    setBusy(true);
    try {
      await apiRequest("/appeals", {
        method: "POST",
        body: JSON.stringify({ message: message.trim() }),
      });
      setSubmitted(true);
      toast.push({
        tone: "success",
        title: "Appeal submitted",
        description: "We’ll review your appeal. You’ll be notified of the outcome.",
      });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Could not submit appeal",
        description:
          err instanceof ApiError ? err.detail : "Try again in a moment.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="bg-background py-16 sm:py-20">
      <Container
        width="narrow"
        className="space-y-6 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
      >
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-heading">Account suspended</h1>
          <p className="text-muted-foreground">
            Your Pàdéyá account is suspended. Review the details below and
            submit an appeal if you believe this should be reversed.
          </p>
        </div>

        {suspension ? (
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">Reason category</dt>
              <dd className="font-medium text-foreground">
                {suspension.reason_category_label}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Duration</dt>
              <dd className="font-medium text-foreground">
                {suspension.duration_label}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Started</dt>
              <dd className="font-medium text-foreground">
                {formatDateTime(suspension.starts_at)}
              </dd>
            </div>
            {suspension.ends_at ? (
              <div>
                <dt className="text-muted-foreground">Ends</dt>
                <dd className="font-medium text-foreground">
                  {formatDateTime(suspension.ends_at)}
                </dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <Alert tone="warning" title="Suspension details">
            Your account is suspended. Sign in again later if details don’t load.
          </Alert>
        )}

        {submitted || payload?.pending_appeal ? (
          <Alert tone="info" title="Appeal pending">
            Your appeal was submitted and is waiting for review. You’ll get an
            in-app and email update when there’s a decision.
          </Alert>
        ) : (
          <form onSubmit={(e) => void onAppeal(e)} className="space-y-3">
            <Textarea
              label="Appeal message"
              name="appeal"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={5}
              required
              minLength={10}
              placeholder="Explain why your account should be restored…"
            />
            <Button
              type="submit"
              disabled={busy || message.trim().length < 10}
            >
              {busy ? "Submitting…" : "Submit appeal"}
            </Button>
          </form>
        )}

        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          <Link href="/">
            <Button variant="secondary" size="sm">
              Back to home
            </Button>
          </Link>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => void logout()}
          >
            Log out
          </Button>
        </div>
      </Container>
    </main>
  );
}
