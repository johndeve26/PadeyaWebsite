"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, type FormEvent, useEffect } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { AuthPasswordField } from "@/components/auth/AuthPasswordField";
import { LoginPageLayout } from "@/components/auth/LoginPageLayout";
import { Alert, Button, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { safeNextPath } from "@/lib/auth/safe-next";
import { consumeSessionExpiredMessage } from "@/lib/auth/session-expired";
import { fetchHostWorkspaces } from "@/lib/hosts-api";

const GENERIC_LOGIN_ERROR =
  "Incorrect username, email, or password. Check your details and try again.";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loginId, setLoginId] = useState(() => searchParams.get("email") || "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [sessionNotice, setSessionNotice] = useState<string | null>(null);

  useEffect(() => {
    setSessionNotice(consumeSessionExpiredMessage());
  }, []);

  const registerHref = useMemo(() => {
    const next = searchParams.get("next");
    if (!next) return "/register";
    return `/register?next=${encodeURIComponent(safeNextPath(next))}`;
  }, [searchParams]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(loginId, password);
      const next = searchParams.get("next");
      if (next) {
        router.push(safeNextPath(next));
        return;
      }
      try {
        const workspaces = await fetchHostWorkspaces();
        if (workspaces.length > 0) {
          router.push("/workspaces");
          return;
        }
      } catch {
        /* fall through */
      }
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(GENERIC_LOGIN_ERROR);
      } else if (err instanceof ApiError && err.detail) {
        setError(GENERIC_LOGIN_ERROR);
      } else {
        setError("We could not sign you in right now. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <LoginPageLayout
      title="Welcome back"
      description="Log in to manage tickets, merch orders, Fan Passport, Vault unlocks, and host tools."
      footer={
        <div className="space-y-4 border-t border-paper/10 pt-5 text-sm">
          <p className="text-paper/80">
            New here?{" "}
            <Link
              href={registerHref}
              className="font-bold text-[#8EF012] hover:underline"
            >
              Create an account
            </Link>
          </p>
          <p className="text-paper/75">
            Bought as a guest?{" "}
            <Link
              href="/checkout/claim"
              className="font-semibold text-[#8EF012] underline-offset-2 hover:underline"
            >
              Find your ticket or order
            </Link>
          </p>
          <p className="text-center text-paper/65">
            <Link
              href="/events"
              className="font-semibold text-paper underline-offset-2 hover:text-[#8EF012] hover:underline"
            >
              Continue browsing events
            </Link>
          </p>
        </div>
      }
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        {sessionNotice ? (
          <Alert tone="warning" title="Session ended">
            {sessionNotice}
          </Alert>
        ) : null}
        <p className="text-sm text-paper/75">
          You&apos;ll stay signed in on this device unless you log out.
        </p>
        <Input
          label="Email or username"
          name="login"
          type="text"
          autoComplete="username"
          required
          surface="onDark"
          hint="Use the email or username you registered with"
          value={loginId}
          onChange={(e) => setLoginId(e.target.value)}
        />
        <AuthPasswordField
          value={password}
          onChange={setPassword}
          required
          surface="onDark"
        />
        <div className="flex justify-end">
          <Link
            href="/forgot-password"
            className="text-sm font-semibold text-[#8EF012] hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        {error ? (
          <Alert tone="danger" title="Could not log in">
            {error}
          </Alert>
        ) : null}
        <Button type="submit" className="w-full" size="lg" disabled={submitting}>
          {submitting ? "Signing in…" : "Log in"}
        </Button>
      </form>
    </LoginPageLayout>
  );
}
