"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { AuthPasswordField } from "@/components/auth/AuthPasswordField";
import { LoginPageLayout } from "@/components/auth/LoginPageLayout";
import { Alert, Button, Input, SkeletonLoader } from "@/components/ui";
import {
  ApiError,
  confirmPasswordReset,
  requestPasswordReset,
  verifyPasswordReset,
} from "@/lib/api";
import {
  formatPasswordResetCooldown,
  PASSWORD_RESET_RESEND_COOLDOWN_SEC,
  passwordResetCooldownSeconds,
} from "@/lib/auth/password-reset-cooldown";

type Phase = "code" | "password" | "done";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialEmail = searchParams.get("email")?.trim().toLowerCase() || "";
  const initialStep = searchParams.get("step") === "password" ? "password" : "code";
  const cooldownBootstrapped = useRef(false);

  const [phase, setPhase] = useState<Phase>(
    initialStep === "password" && initialEmail ? "password" : "code",
  );
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [verifiedCode, setVerifiedCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [resendNotice, setResendNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendCooldownSec, setResendCooldownSec] = useState(0);
  const [editingEmail, setEditingEmail] = useState(!initialEmail);

  useEffect(() => {
    if (cooldownBootstrapped.current) return;
    cooldownBootstrapped.current = true;
    const fromQuery = Number.parseInt(searchParams.get("cooldown") ?? "", 10);
    if (Number.isFinite(fromQuery) && fromQuery > 0) {
      setResendCooldownSec(fromQuery);
      return;
    }
    if (searchParams.get("sent") === "1") {
      setResendCooldownSec(PASSWORD_RESET_RESEND_COOLDOWN_SEC);
    }
  }, [searchParams]);

  useEffect(() => {
    if (resendCooldownSec <= 0) return;
    const timer = window.setInterval(() => {
      setResendCooldownSec((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCooldownSec]);

  const normalizedCode = useMemo(
    () => code.trim().toUpperCase().replace(/[\s-]/g, "").slice(0, 6),
    [code],
  );

  async function onResendCode() {
    setError(null);
    setResendNotice(null);
    if (!email.trim()) {
      setError("Enter your email before requesting a new code.");
      return;
    }
    setResending(true);
    try {
      await requestPasswordReset(email.trim());
      setCode("");
      setVerifiedCode("");
      setResendNotice(`We sent a new code to ${email.trim()}.`);
      setResendCooldownSec(PASSWORD_RESET_RESEND_COOLDOWN_SEC);
      setEditingEmail(false);
    } catch (err) {
      if (err instanceof ApiError) {
        const wait = passwordResetCooldownSeconds(err);
        if (wait) setResendCooldownSec(wait);
        setError(err.detail);
      } else {
        setError("Could not send a new code. Please try again.");
      }
    } finally {
      setResending(false);
    }
  }

  async function onVerifyCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResendNotice(null);
    if (!email.trim()) {
      setError("Enter the email on your account.");
      return;
    }
    if (normalizedCode.length !== 6) {
      setError("Enter the 6-character code from your email.");
      return;
    }
    setSubmitting(true);
    try {
      await verifyPasswordReset({ email: email.trim(), code: normalizedCode });
      setVerifiedCode(normalizedCode);
      setPhase("password");
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "That code is invalid or expired. Request a new one below.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function onSetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      await confirmPasswordReset({
        email: email.trim(),
        code: verifiedCode,
        new_password: password,
      });
      setPhase("done");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not reset password. Your code may have expired — request a new one.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (phase === "done") {
    return (
      <LoginPageLayout
        title="Password updated"
        description="Your Pàdéyá password has been changed. Sign in with your username or email and new password."
        footer={
          <p className="text-sm text-paper/70">
            <Link
              href="/login"
              className="font-semibold text-[#8EF012] hover:underline"
            >
              Go to log in
            </Link>
          </p>
        }
      >
        <Button type="button" className="w-full" size="lg" onClick={() => router.push("/login")}>
          Log in
        </Button>
      </LoginPageLayout>
    );
  }

  if (phase === "password") {
    return (
      <LoginPageLayout
        title="Choose a new password"
        description="Code verified. Set a new password for your account. Codes expire after 5 minutes."
        footer={
          <p className="text-sm text-paper/70">
            <button
              type="button"
              className="font-semibold text-[#8EF012] hover:underline"
              onClick={() => {
                setPhase("code");
                setPassword("");
                setConfirm("");
                setError(null);
                setResendNotice(null);
              }}
            >
              Use a different code
            </button>
          </p>
        }
      >
        <form className="space-y-4" onSubmit={onSetPassword}>
          <p className="text-sm leading-relaxed text-paper/80">
            Resetting password for{" "}
            <span className="font-semibold text-paper">{email}</span>
          </p>
          {error ? (
            <Alert tone="danger" title="Could not update password">
              {error}
            </Alert>
          ) : null}
          <AuthPasswordField
            label="New password"
            name="password"
            autoComplete="new-password"
            required
            minLength={8}
            surface="onDark"
            hint="At least 8 characters"
            value={password}
            onChange={setPassword}
          />
          <AuthPasswordField
            label="Confirm password"
            name="confirm-password"
            autoComplete="new-password"
            required
            minLength={8}
            surface="onDark"
            value={confirm}
            onChange={setConfirm}
          />
          <Button type="submit" className="w-full" size="lg" disabled={submitting}>
            {submitting ? "Updating…" : "Update password"}
          </Button>
        </form>
      </LoginPageLayout>
    );
  }

  const showEmailAsSent = email.trim().length > 0 && !editingEmail;

  return (
    <LoginPageLayout
      title="Enter reset code"
      description={
        showEmailAsSent
          ? "Enter the 6-character code from your email. Codes expire after 5 minutes."
          : "Enter your account email, send a code, then enter it here."
      }
      footer={
        <p className="text-sm text-paper/70">
          <Link
            href="/login"
            className="font-semibold text-[#8EF012] hover:underline"
          >
            Back to log in
          </Link>
        </p>
      }
    >
      <form className="space-y-4" onSubmit={onVerifyCode}>
        {resendNotice ? (
          <Alert tone="success" title="New code sent">
            {resendNotice}
          </Alert>
        ) : null}
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}
        {showEmailAsSent ? (
          <div className="space-y-2 rounded-[var(--radius-lg)] border border-paper/10 bg-paper/[0.04] px-4 py-3">
            <p className="text-sm leading-relaxed text-paper/85">
              A code has been sent to{" "}
              <span className="font-semibold break-all text-paper">{email}</span>
            </p>
            <button
              type="button"
              className="text-sm font-semibold text-[#8EF012] hover:underline"
              onClick={() => {
                setEditingEmail(true);
                setCode("");
                setVerifiedCode("");
                setResendNotice(null);
                setError(null);
              }}
            >
              Change email
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Input
              label="Email"
              name="email"
              type="email"
              inputMode="email"
              autoComplete="email"
              required
              surface="onDark"
              value={email}
              onChange={(e) => setEmail(e.target.value.trim().toLowerCase())}
            />
            {email.trim() && editingEmail ? (
              <button
                type="button"
                className="text-sm font-semibold text-paper/70 underline-offset-2 hover:text-[#8EF012] hover:underline"
                onClick={() => {
                  if (email.trim()) setEditingEmail(false);
                }}
              >
                Cancel
              </button>
            ) : null}
          </div>
        )}
        <Input
          label="Reset code"
          name="code"
          type="text"
          inputMode="text"
          autoComplete="one-time-code"
          required
          surface="onDark"
          hint="6 letters or numbers from your email"
          value={code}
          onChange={(e) =>
            setCode(
              e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 6),
            )
          }
        />
        <Button type="submit" className="w-full" size="lg" disabled={submitting || !email.trim()}>
          {submitting ? "Checking…" : "Continue"}
        </Button>
        <Button
          type="button"
          variant="outline-dark"
          className="w-full"
          disabled={resending || resendCooldownSec > 0 || !email.trim()}
          onClick={() => void onResendCode()}
        >
          {resending
            ? "Sending…"
            : resendCooldownSec > 0
              ? `New code in ${formatPasswordResetCooldown(resendCooldownSec)}`
              : editingEmail || !showEmailAsSent
                ? "Send code"
                : "Email new code"}
        </Button>
      </form>
    </LoginPageLayout>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-[50vh] bg-ink py-20">
          <div className="mx-auto max-w-md px-4">
            <SkeletonLoader lines={4} />
          </div>
        </main>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
