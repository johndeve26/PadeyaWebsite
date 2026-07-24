"use client";

import { useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { AuthPasswordField } from "@/components/auth/AuthPasswordField";
import { Alert, Button, Card, Input, SectionHeader, useToast } from "@/components/ui";
import { ApiError, changeEmail, changePassword } from "@/lib/api";
import { markSessionExpired } from "@/lib/auth/session-expired";

type Props = {
  email: string;
  onEmailChanged: () => Promise<void>;
};

export function AccountSecurityCard({ email, onEmailChanged }: Props) {
  const toast = useToast();
  const { logout } = useAuth();

  const [currentPasswordForEmail, setCurrentPasswordForEmail] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  async function onChangeEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEmailError(null);
    setEmailBusy(true);
    try {
      await changeEmail({
        new_email: newEmail.trim().toLowerCase(),
        current_password: currentPasswordForEmail,
      });
      setNewEmail("");
      setCurrentPasswordForEmail("");
      markSessionExpired(
        "Your email was updated. Sign in again with your new email.",
      );
      await logout();
      window.location.href = "/login";
      return;
    } catch (err) {
      setEmailError(
        err instanceof ApiError ? err.detail : "Could not update email",
      );
    } finally {
      setEmailBusy(false);
    }
  }

  async function onChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }
    setPasswordBusy(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      markSessionExpired(
        "Your password was updated. Sign in again with your new password.",
      );
      await logout();
      window.location.href = "/login";
      return;
    } catch (err) {
      setPasswordError(
        err instanceof ApiError ? err.detail : "Could not update password",
      );
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <Card className="max-w-2xl space-y-8">
      <SectionHeader
        eyebrow="Security"
        title="Email & password"
        description="Update sign-in credentials. We email you when something changes."
      />

      <form className="space-y-4 border-b border-border pb-8" onSubmit={onChangeEmail}>
        <p className="text-sm text-muted-foreground">
          Current email:{" "}
          <span className="font-semibold text-foreground break-all">{email}</span>
        </p>
        {emailError ? (
          <Alert tone="danger" title="Could not change email">
            {emailError}
          </Alert>
        ) : null}
        <Input
          label="New email"
          name="new_email"
          type="email"
          autoComplete="email"
          required
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
        />
        <AuthPasswordField
          label="Current password"
          name="current_password_email"
          autoComplete="current-password"
          required
          value={currentPasswordForEmail}
          onChange={setCurrentPasswordForEmail}
        />
        <Button type="submit" disabled={emailBusy || !newEmail.trim()}>
          {emailBusy ? "Updating…" : "Update email"}
        </Button>
      </form>

      <form className="space-y-4" onSubmit={onChangePassword}>
        {passwordError ? (
          <Alert tone="danger" title="Could not change password">
            {passwordError}
          </Alert>
        ) : null}
        <AuthPasswordField
          label="Current password"
          name="current_password"
          autoComplete="current-password"
          required
          value={currentPassword}
          onChange={setCurrentPassword}
        />
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
        <Button type="submit" disabled={passwordBusy}>
          {passwordBusy ? "Updating…" : "Update password"}
        </Button>
      </form>
    </Card>
  );
}
