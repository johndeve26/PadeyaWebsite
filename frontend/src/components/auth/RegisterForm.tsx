"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { AuthPasswordField } from "@/components/auth/AuthPasswordField";
import { LoginPageLayout } from "@/components/auth/LoginPageLayout";
import {
  ProfileLocationTaxonomyFields,
  type ProfileLocationLabels,
} from "@/components/discovery/ProfileLocationTaxonomyFields";
import { Alert, Button, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { writeRegisterLocationSeed } from "@/lib/auth/register-location";
import { safeNextPath } from "@/lib/auth/safe-next";
import {
  normalizePassportUsername,
  PASSPORT_USERNAME_PATTERN,
} from "@/lib/passport/username";

import { registerErrorMessage } from "@/lib/auth/register-errors";
import { brand } from "@/lib/brand";
import {
  fetchTransferClaimContext,
  resolveRegisterEmailFromSearchParams,
} from "@/lib/tickets/claim-context";

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initial = useMemo(
    () => resolveRegisterEmailFromSearchParams(searchParams),
    [searchParams],
  );
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(() => initial.email);
  const [emailFromClaim, setEmailFromClaim] = useState(Boolean(initial.email));
  const [password, setPassword] = useState("");
  const [location, setLocation] = useState<ProfileLocationLabels>({
    country: "",
    state: "",
    city: "",
  });
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const normalizedUsername = useMemo(
    () => normalizePassportUsername(username),
    [username],
  );

  const loginHref = useMemo(() => {
    const next = searchParams.get("next");
    if (!next) return "/login";
    const base = `/login?next=${encodeURIComponent(safeNextPath(next))}`;
    if (email.trim()) {
      return `${base}&email=${encodeURIComponent(email.trim().toLowerCase())}`;
    }
    return base;
  }, [searchParams, email]);

  useEffect(() => {
    if (initial.email) {
      setEmail(initial.email);
      setEmailFromClaim(true);
      return;
    }
    if (!initial.token) return;
    let active = true;
    void (async () => {
      try {
        const ctx = await fetchTransferClaimContext(initial.token!);
        if (!active) return;
        setEmail(ctx.recipient_email.trim().toLowerCase());
        setEmailFromClaim(true);
      } catch {
        // invalid token — leave email blank
      }
    })();
    return () => {
      active = false;
    };
  }, [initial.email, initial.token]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!PASSPORT_USERNAME_PATTERN.test(normalizedUsername)) {
      setError(
        "Username must be 3–32 characters: lowercase letters, numbers, underscore.",
      );
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (!acceptedTerms) {
      setError("Accept the Terms of Service to create your account.");
      return;
    }
    setSubmitting(true);
    try {
      await register({
        email,
        password,
        username: normalizedUsername,
      });
      writeRegisterLocationSeed(location);
      const next = searchParams.get("next");
      router.push(next ? safeNextPath(next) : "/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(registerErrorMessage(err));
      } else {
        setError("We could not create your account right now. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <LoginPageLayout
      title="Create your account"
      description="Pick a username once — it becomes your default on Fan Passport, and the starting point for host legacy and public fan pages."
      footer={
        <div className="space-y-4 border-t border-paper/10 pt-5 text-sm">
          <p className="text-paper/80">
            Already have an account?{" "}
            <Link
              href={loginHref}
              className="font-bold text-[#8EF012] hover:underline"
            >
              Log in
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
        <Input
          label="Username"
          name="username"
          autoComplete="username"
          required
          surface="onDark"
          hint={
            normalizedUsername
              ? `Your fan page: /f/${normalizedUsername}`
              : "Lowercase letters, numbers, underscore — 3 to 32 characters"
          }
          value={username}
          onChange={(e) =>
            setUsername(normalizePassportUsername(e.target.value))
          }
        />
        <Input
          label="Email"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          surface="onDark"
          hint={
            emailFromClaim
              ? "Locked to the recipient email for this ticket transfer"
              : "Used for login and ticket delivery"
          }
          value={email}
          readOnly={emailFromClaim}
          onChange={(e) => {
            if (emailFromClaim) return;
            setEmail(e.target.value);
          }}
        />
        <AuthPasswordField
          label="Password"
          name="password"
          autoComplete="new-password"
          required
          minLength={8}
          surface="onDark"
          hint="At least 8 characters"
          value={password}
          onChange={setPassword}
        />
        <ProfileLocationTaxonomyFields
          value={location}
          onChange={setLocation}
          seed={{ country: "Nigeria" }}
          hint="Optional — pre-fills host onboarding if you become a host later."
        />
        <label className="flex cursor-pointer items-start gap-2.5 text-sm leading-snug text-paper/85">
          <input
            type="checkbox"
            name="accept_terms"
            required
            checked={acceptedTerms}
            onChange={(e) => {
              setAcceptedTerms(e.target.checked);
              if (e.target.checked) setError(null);
            }}
            className="mt-0.5 h-4 w-4 shrink-0 rounded border border-paper/35 bg-black/45 accent-[#8EF012]"
          />
          <span>
            I agree to the{" "}
            <Link
              href="/terms"
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-[#8EF012] underline-offset-2 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {brand.name} Terms of Service
            </Link>
            .
          </span>
        </label>
        {error ? (
          <Alert tone="danger" title="Could not create account">
            {error}
          </Alert>
        ) : null}
        <Button
          type="submit"
          className="w-full"
          size="lg"
          disabled={submitting || !acceptedTerms}
        >
          {submitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </LoginPageLayout>
  );
}
