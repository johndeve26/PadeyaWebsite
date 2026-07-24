"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { LoginPageLayout } from "@/components/auth/LoginPageLayout";
import { Alert, Button, Input, SkeletonLoader } from "@/components/ui";
import { ApiError, confirmEmailVerification, requestEmailVerification } from "@/lib/api";

function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, refreshUser, loading } = useAuth();
  const linkToken = searchParams.get("token")?.trim() || "";

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [autoVerifying, setAutoVerifying] = useState(Boolean(linkToken));
  const autoVerifyAttempted = useRef(false);

  const normalizedCode = useMemo(
    () => code.trim().toUpperCase().replace(/[\s-]/g, "").slice(0, 6),
    [code],
  );

  async function completeVerification(input: { token?: string; code?: string }) {
    await confirmEmailVerification(input);
    await refreshUser();
    router.replace("/dashboard");
  }

  useEffect(() => {
    if (loading || !linkToken || autoVerifyAttempted.current) {
      return;
    }
    autoVerifyAttempted.current = true;
    setAutoVerifying(true);
    setError(null);
    void (async () => {
      try {
        await completeVerification({ token: linkToken });
      } catch (err) {
        autoVerifyAttempted.current = false;
        setAutoVerifying(false);
        setError(
          err instanceof ApiError
            ? err.detail
            : "Could not verify your email. Try again or request a new email.",
        );
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- verify once when token present
  }, [loading, linkToken]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);
    try {
      await completeVerification({
        token: linkToken || undefined,
        code: linkToken ? undefined : normalizedCode || undefined,
      });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not verify your email. Try again or request a new email.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function onResend() {
    if (!user) {
      router.push("/login?next=/verify");
      return;
    }
    setResending(true);
    setError(null);
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
      setResending(false);
    }
  }

  if (loading || autoVerifying) {
    return (
      <LoginPageLayout
        title="Verifying your email"
        description="One moment — we are confirming your address and taking you to your dashboard."
      >
        <SkeletonLoader className="mx-auto max-w-md" lines={3} />
      </LoginPageLayout>
    );
  }

  return (
    <LoginPageLayout
      title="Verify your email"
      description="Secure your Pàdéyá account and receive ticket, merch, Vault, and host updates."
    >
      <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
        {linkToken ? (
          <p className="text-sm text-muted-foreground">
            Your link could not be confirmed automatically. Tap verify below to try again.
          </p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              Enter the 6-character code from your verification email, or open the
              link we sent you.
            </p>
            <Input
              label="Verification code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoComplete="one-time-code"
              inputMode="text"
              maxLength={8}
              required={!linkToken}
            />
          </>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={submitting || (!linkToken && normalizedCode.length !== 6)}
        >
          {submitting ? "Verifying…" : "Verify email"}
        </Button>

        <Button
          type="button"
          variant="ghost"
          className="w-full"
          disabled={resending}
          onClick={() => void onResend()}
        >
          {resending ? "Sending…" : "Resend verification email"}
        </Button>

        {!user ? (
          <p className="text-center text-xs text-muted-foreground">
            <Link href="/login?next=/verify" className="font-semibold underline-offset-2 hover:underline">
              Log in
            </Link>{" "}
            to enter a code or resend verification.
          </p>
        ) : null}

        {notice ? (
          <Alert tone="success" title="Done">
            {notice}
          </Alert>
        ) : null}
        {error ? (
          <Alert tone="danger" title="Verification failed">
            {error}
          </Alert>
        ) : null}
      </form>
    </LoginPageLayout>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<SkeletonLoader className="mx-auto max-w-md" />}>
      <VerifyEmailForm />
    </Suspense>
  );
}
