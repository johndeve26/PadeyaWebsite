"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { AuthPasswordField } from "@/components/auth/AuthPasswordField";
import { Alert, Button, Card, Input, SectionHeader, useToast } from "@/components/ui";
import {
  changeEmail,
  changePassword,
  confirmEmailChange,
} from "@/lib/api";
import { errorDetail } from "@/lib/api-timeouts";
import { emailVerifyPath } from "@/lib/auth/email-verify-path";

type Props = {
  email: string;
  onEmailChanged: () => Promise<void>;
};

export function AccountSecurityCard({ email, onEmailChanged }: Props) {
  const toast = useToast();
  const router = useRouter();
  const { isImpersonating, user } = useAuth();
  const canChangeCredentials =
    !isImpersonating ||
    Boolean(user?.impersonation?.scopes?.includes("credentials"));

  const [currentPasswordForEmail, setCurrentPasswordForEmail] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [emailCode, setEmailCode] = useState("");
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);
  const [emailNotice, setEmailNotice] = useState<string | null>(null);
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const normalizedEmailCode = useMemo(
    () => emailCode.trim().toUpperCase().replace(/[\s-]/g, "").slice(0, 6),
    [emailCode],
  );

  async function onRequestEmailChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canChangeCredentials) return;
    setEmailError(null);
    setEmailNotice(null);
    setEmailBusy(true);
    try {
      const result = await changeEmail({
        new_email: newEmail.trim().toLowerCase(),
        current_password:
          isImpersonating && canChangeCredentials
            ? ""
            : currentPasswordForEmail,
      });
      if (result.status === "updated") {
        setNewEmail("");
        setCurrentPasswordForEmail("");
        setPendingEmail(null);
        setEmailCode("");
        await onEmailChanged();
        if (isImpersonating) {
          toast.push({
            tone: "success",
            title: "Email updated for this account (audited impersonation).",
          });
          return;
        }
        toast.push({
          tone: "success",
          title: "Email updated. Verify the new address to keep using your dashboard.",
        });
        router.replace(emailVerifyPath("/dashboard/settings"));
        return;
      }
      setPendingEmail(result.pending_email);
      setEmailNotice(result.message);
      setEmailCode("");
    } catch (err) {
      setEmailError(errorDetail(err, "Could not update email"));
    } finally {
      setEmailBusy(false);
    }
  }

  async function onConfirmEmailChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canChangeCredentials || !pendingEmail) return;
    if (normalizedEmailCode.length !== 6) {
      setEmailError("Enter the 6-character code from your new email.");
      return;
    }
    setEmailError(null);
    setEmailNotice(null);
    setEmailBusy(true);
    try {
      await confirmEmailChange({ code: normalizedEmailCode });
      setNewEmail("");
      setCurrentPasswordForEmail("");
      setPendingEmail(null);
      setEmailCode("");
      await onEmailChanged();
      toast.push({
        tone: "success",
        title:
          "Email updated. Other devices were signed out — verify your new address next.",
      });
      router.replace(emailVerifyPath("/dashboard/settings"));
    } catch (err) {
      setEmailError(errorDetail(err, "Could not confirm email change"));
    } finally {
      setEmailBusy(false);
    }
  }

  async function onChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canChangeCredentials) return;
    setPasswordError(null);
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }
    setPasswordBusy(true);
    try {
      await changePassword({
        current_password:
          isImpersonating && canChangeCredentials ? "" : currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.push({
        tone: "success",
        title: isImpersonating
          ? "Password updated for this account. Their sessions were signed out (audited)."
          : "Password updated. You stay signed in here; other devices were signed out.",
      });
    } catch (err) {
      setPasswordError(errorDetail(err, "Could not update password"));
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <Card className="max-w-2xl space-y-8">
      <SectionHeader
        eyebrow="Security"
        title="Email & password"
        description={
          isImpersonating && canChangeCredentials
            ? "Full impersonation pack may update this account’s credentials without the current password. Changes are audited."
            : isImpersonating
              ? "Credential changes require the full (super admin) impersonation pack."
              : "Update sign-in credentials. You stay signed in on this device; other sessions are signed out. Email changes need a code at the new address, then email verification."
        }
      />

      {isImpersonating && canChangeCredentials ? (
        <Alert tone="warning" title="Impersonation credential change">
          You are changing credentials for the impersonated user. Prefer a clear
          support reason in the session audit trail.
        </Alert>
      ) : null}

      {isImpersonating && !canChangeCredentials ? (
        <Alert tone="warning" title="Credentials locked for this pack">
          Your impersonation pack is view or host-events only. Ask a super admin
          for credential recovery, or use Force password reset from Admin → Users.
        </Alert>
      ) : null}

      <fieldset
        disabled={!canChangeCredentials}
        className="space-y-8 disabled:opacity-70"
        data-impersonation-credentials-locked={
          isImpersonating && !canChangeCredentials ? "true" : "false"
        }
      >
      <div className="space-y-4 border-b border-border pb-8">
        <p className="text-sm text-muted-foreground">
          Current email:{" "}
          <span className="font-semibold text-foreground break-all">{email}</span>
        </p>
        {emailError ? (
          <Alert tone="danger" title="Could not change email">
            {emailError}
          </Alert>
        ) : null}
        {emailNotice ? (
          <Alert tone="success" title="Confirmation required">
            {emailNotice}
          </Alert>
        ) : null}

        {!pendingEmail || isImpersonating ? (
          <form className="space-y-4" onSubmit={(e) => void onRequestEmailChange(e)}>
            <Input
              label="New email"
              name="new_email"
              type="email"
              autoComplete="email"
              required
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
            />
            {!isImpersonating ? (
              <AuthPasswordField
                label="Current password"
                name="current_password_email"
                autoComplete="current-password"
                required
                value={currentPasswordForEmail}
                onChange={setCurrentPasswordForEmail}
              />
            ) : null}
            <Button
              type="submit"
              disabled={!canChangeCredentials || emailBusy || !newEmail.trim()}
            >
              {emailBusy
                ? isImpersonating
                  ? "Updating…"
                  : "Sending code…"
                : isImpersonating
                  ? "Update email"
                  : "Send confirmation code"}
            </Button>
          </form>
        ) : (
          <form className="space-y-4" onSubmit={(e) => void onConfirmEmailChange(e)}>
            <p className="text-sm text-muted-foreground">
              Enter the 6-character code we sent to{" "}
              <span className="font-semibold text-foreground break-all">
                {pendingEmail}
              </span>
              . Your sign-in email stays{" "}
              <span className="font-semibold text-foreground break-all">{email}</span>{" "}
              until you confirm.
            </p>
            <Input
              label="Confirmation code"
              name="email_change_code"
              value={emailCode}
              onChange={(e) => setEmailCode(e.target.value)}
              autoComplete="one-time-code"
              inputMode="text"
              maxLength={8}
              spellCheck={false}
              required
              placeholder="e.g. AU33XW"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                disabled={
                  !canChangeCredentials ||
                  emailBusy ||
                  normalizedEmailCode.length !== 6
                }
              >
                {emailBusy ? "Confirming…" : "Confirm email change"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={emailBusy}
                onClick={() => {
                  setPendingEmail(null);
                  setEmailCode("");
                  setEmailNotice(null);
                  setEmailError(null);
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        )}
      </div>

      <form className="space-y-4" onSubmit={onChangePassword}>
        {passwordError ? (
          <Alert tone="danger" title="Could not change password">
            {passwordError}
          </Alert>
        ) : null}
        {!isImpersonating ? (
          <AuthPasswordField
            label="Current password"
            name="current_password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={setCurrentPassword}
          />
        ) : null}
        <AuthPasswordField
          label="New password"
          name="new_password"
          autoComplete="new-password"
          required
          minLength={8}
          hint="At least 8 characters"
          value={newPassword}
          onChange={setNewPassword}
        />
        <AuthPasswordField
          label="Confirm new password"
          name="confirm_new_password"
          autoComplete="new-password"
          required
          minLength={8}
          value={confirmPassword}
          onChange={setConfirmPassword}
        />
        <Button type="submit" disabled={!canChangeCredentials || passwordBusy}>
          {passwordBusy ? "Updating…" : "Update password"}
        </Button>
      </form>
      </fieldset>
    </Card>
  );
}
