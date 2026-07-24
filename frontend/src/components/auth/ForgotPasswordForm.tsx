"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { LoginPageLayout } from "@/components/auth/LoginPageLayout";
import { Alert, Button, Input } from "@/components/ui";
import { ApiError, requestPasswordReset } from "@/lib/api";
import { passwordResetCooldownSeconds } from "@/lib/auth/password-reset-cooldown";

export function ForgotPasswordForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const normalized = email.trim().toLowerCase();
    try {
      await requestPasswordReset(normalized);
      router.push(
        `/reset-password?email=${encodeURIComponent(normalized)}&step=code&sent=1`,
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 429 && normalized) {
        const wait = passwordResetCooldownSeconds(err);
        const cooldownQuery =
          wait && wait > 0 ? `&cooldown=${encodeURIComponent(String(wait))}` : "";
        router.push(
          `/reset-password?email=${encodeURIComponent(normalized)}&step=code${cooldownQuery}`,
        );
        return;
      }
      setError(
        err instanceof ApiError
          ? err.detail
          : "We could not send a reset code right now. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <LoginPageLayout
      title="Reset your password"
      description="Enter your account email. On the next screen you will enter the code from your email, then choose a new password."
      footer={
        <p className="text-center text-sm text-paper/65">
          <Link
            href="/login"
            className="font-semibold text-[#8EF012] hover:underline"
          >
            Back to log in
          </Link>
        </p>
      }
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        <Input
          label="Email"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          surface="onDark"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        {error ? (
          <Alert tone="danger" title="Could not send reset code">
            {error}
          </Alert>
        ) : null}
        <Button type="submit" className="w-full" size="lg" disabled={submitting}>
          {submitting ? "Sending…" : "Email reset code"}
        </Button>
      </form>
    </LoginPageLayout>
  );
}
