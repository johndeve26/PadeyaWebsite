"use client";

import { useMemo, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Alert, Button, Input } from "@/components/ui";
import {
  confirmEmailVerification,
  requestEmailVerification,
} from "@/lib/api";
import { errorDetail } from "@/lib/api-timeouts";

const BANNER_COPY =
  "Verify your email to secure your Pàdéyá account and receive ticket, merch, Vault, and host updates.";

type EmailVerificationBannerProps = {
  className?: string;
};

export function EmailVerificationBanner({
  className = "",
}: EmailVerificationBannerProps) {
  const { user, refreshUser, loading } = useAuth();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState<"verify" | "resend" | "refresh" | null>(
    null,
  );
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const normalizedCode = useMemo(
    () => code.trim().toUpperCase().replace(/[\s-]/g, "").slice(0, 6),
    [code],
  );

  if (loading || !user || user.is_verified) {
    return null;
  }

  async function onVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (normalizedCode.length !== 6) {
      setError("Enter the 6-character code from your email.");
      return;
    }
    setBusy("verify");
    setError(null);
    setNotice(null);
    try {
      await confirmEmailVerification({ code: normalizedCode });
      await refreshUser();
      setCode("");
      setNotice("Email verified.");
    } catch (err) {
      setError(errorDetail(err, "Could not verify your email."));
    } finally {
      setBusy(null);
    }
  }

  async function onResend() {
    setBusy("resend");
    setError(null);
    setNotice(null);
    try {
      const message = await requestEmailVerification();
      setNotice(message || "Check your inbox for a verification email.");
    } catch (err) {
      setError(errorDetail(err, "Could not send verification email."));
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
    } catch (err) {
      setError(errorDetail(err, "Could not refresh your account status."));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Alert tone="warning" title="Verify your email" className={className}>
      <div className="space-y-3">
        <p>{BANNER_COPY}</p>
        <p className="text-sm opacity-90">
          Enter the 6-character code from your email, or open the link we sent
          you.
        </p>
        <form
          onSubmit={(event) => void onVerify(event)}
          className="flex flex-col gap-2 sm:flex-row sm:items-end"
        >
          <div className="min-w-0 flex-1 sm:max-w-xs">
            <Input
              label="Verification code"
              name="verification_code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoComplete="one-time-code"
              inputMode="text"
              maxLength={8}
              spellCheck={false}
              disabled={busy !== null}
              placeholder="e.g. AU33XW"
            />
          </div>
          <Button
            type="submit"
            size="sm"
            disabled={busy !== null || normalizedCode.length !== 6}
          >
            {busy === "verify" ? "Verifying…" : "Verify email"}
          </Button>
        </form>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
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
            {busy === "refresh"
              ? "Refreshing…"
              : "I have verified, refresh status"}
          </Button>
        </div>
        {error ? <p className="text-sm font-medium">{error}</p> : null}
        {notice ? <p className="text-sm opacity-90">{notice}</p> : null}
      </div>
    </Alert>
  );
}

export { BANNER_COPY as EMAIL_VERIFICATION_BANNER_COPY };
