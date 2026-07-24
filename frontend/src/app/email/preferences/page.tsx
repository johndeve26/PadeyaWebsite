"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { ExpiredLinkState } from "@/components/not-found/ExpiredLinkState";
import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchEmailPreferencesByToken,
  updateEmailPreferencesByToken,
  type EmailPreferences,
} from "@/lib/email-api";

export default function EmailPreferencesTokenPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-muted-foreground">Loading…</p>}>
      <PrefsInner />
    </Suspense>
  );
}

function PrefsInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [prefs, setPrefs] = useState<EmailPreferences | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    let active = true;
    void (async () => {
      try {
        const data = await fetchEmailPreferencesByToken(token);
        if (active) setPrefs(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Invalid or expired link");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [token]);

  async function setMarketing(on: boolean) {
    if (!token) return;
    setBusy(true);
    try {
      const next = await updateEmailPreferencesByToken(token, {
        email_marketing: on,
      });
      setPrefs(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <ExpiredLinkState
        title="This link has expired"
        description="This email preferences link is invalid or no longer valid. Sign in to manage notifications from your dashboard settings."
        primaryHref="/dashboard/settings/notifications"
        primaryLabel="Notification settings"
      />
    );
  }

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-lg flex-col justify-center px-4 py-16">
      <Card className="space-y-4">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Pàdéyá
        </p>
        <h1 className="text-2xl font-extrabold">Email preferences</h1>
        {!token ? (
          <Alert tone="warning" title="Missing token">
            Open this page from an email link, or sign in to Settings → Notifications.
          </Alert>
        ) : null}
        {prefs ? (
          <>
            <p className="text-sm text-muted-foreground">
              Marketing emails:{" "}
              <strong>{prefs.email_marketing ? "on" : "off"}</strong>
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={busy || !prefs.email_marketing}
                onClick={() => void setMarketing(false)}
              >
                Turn marketing off
              </Button>
              <Button
                variant="secondary"
                disabled={busy || prefs.email_marketing}
                onClick={() => void setMarketing(true)}
              >
                Turn marketing on
              </Button>
            </div>
            <a
              className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
              href="/dashboard/settings/notifications"
            >
              Sign in for full controls
            </a>
          </>
        ) : token && !error ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : null}
      </Card>
    </main>
  );
}
