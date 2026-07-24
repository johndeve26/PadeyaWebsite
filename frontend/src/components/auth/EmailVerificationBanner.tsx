"use client";

import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Alert, Button } from "@/components/ui";
import { ApiError, requestEmailVerification } from "@/lib/api";

const BANNER_COPY =
  "Verify your email to secure your Pàdéyá account and receive ticket, merch, Vault, and host updates.";

type EmailVerificationBannerProps = {
  className?: string;
};

export function EmailVerificationBanner({
  className = "",
}: EmailVerificationBannerProps) {
  const { user, refreshUser, loading } = useAuth();
  const [busy, setBusy] = useState<"resend" | "refresh" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (loading || !user || user.is_verified) {
    return null;
  }

  async function onResend() {
    setBusy("resend");
    setError(null);
    setNotice(null);
    try {
      const message = await requestEmailVerification();
      setNotice(message || "Check your inbox for a verification email.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not send verification email.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function onRefresh() {
    setBusy("refresh");
    setError(null);
    try {
      await refreshUser();
      setNotice("Account status updated.");
    } catch {
      setError("Could not refresh your account status.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Alert
      tone="warning"
      title="Verify your email"
      className={className}
      action={
        <div className="flex flex-col gap-2 sm:items-end">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={busy !== null}
            onClick={() => void onResend()}
          >
            {busy === "resend" ? "Sending…" : "Resend verification email"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={busy !== null}
            onClick={() => void onRefresh()}
          >
            {busy === "refresh" ? "Refreshing…" : "I have verified, refresh status"}
          </Button>
        </div>
      }
    >
      <p>{BANNER_COPY}</p>
      {error ? <p className="text-sm font-medium">{error}</p> : null}
      {notice ? <p className="text-sm opacity-90">{notice}</p> : null}
    </Alert>
  );
}

export { BANNER_COPY as EMAIL_VERIFICATION_BANNER_COPY };
