"use client";

import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { EmailVerificationBanner } from "@/components/auth/EmailVerificationBanner";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import { AccountSecurityCard } from "@/components/settings/AccountSecurityCard";
import { NotificationPreferencesSections } from "@/components/notifications/NotificationPreferencesSections";
import { ThemeAppearanceCard } from "@/components/theme/ThemeAppearanceCard";
import {
  Alert,
  Button,
  Card,
  Input,
  SectionHeader,
  useToast,
} from "@/components/ui";
import { updateMyProfile } from "@/lib/admin-lifecycle-api";
import { ApiError } from "@/lib/api";
import { useUnsavedChanges } from "@/lib/hooks/useUnsavedChanges";

export default function DashboardSettingsPage() {
  const { user, refreshUser } = useAuth();
  const toast = useToast();
  const serverDisplayName = user?.full_name ?? "";
  const serverUsername = user?.username ?? "";
  const serverAvatar = user?.avatar_url ?? "";
  const [draftDisplayName, setDraftDisplayName] = useState<string | null>(null);
  const [draftUsername, setDraftUsername] = useState<string | null>(null);
  const [draftAvatar, setDraftAvatar] = useState<string | null>(null);
  const displayName = draftDisplayName ?? serverDisplayName;
  const username = draftUsername ?? serverUsername;
  const avatarUrl = draftAvatar ?? serverAvatar;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    (draftDisplayName !== null &&
      draftDisplayName.trim() !== serverDisplayName.trim()) ||
    (draftUsername !== null && draftUsername.trim() !== serverUsername.trim()) ||
    (draftAvatar !== null && draftAvatar.trim() !== serverAvatar.trim());
  useUnsavedChanges(dirty);

  const email = user?.email ?? "—";

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!displayName.trim()) {
      setError("Display name is required.");
      return;
    }
    if (!username.trim()) {
      setError("Username is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const trimmedAvatar = avatarUrl.trim();
      await updateMyProfile({
        display_name: displayName.trim(),
        username: username.trim().toLowerCase(),
        ...(draftAvatar !== null
          ? trimmedAvatar
            ? { avatar_url: trimmedAvatar }
            : { clear_avatar: true }
          : {}),
      });
      setDraftDisplayName(null);
      setDraftUsername(null);
      setDraftAvatar(null);
      await refreshUser();
      toast.push({ tone: "success", title: "Profile updated" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Account"
      title="Profile & security"
      description="Your photo, display name, username, sign-in email, password, appearance, and notifications."
    >
      {error ? (
        <Alert tone="danger" title="Could not save">
          {error}
        </Alert>
      ) : null}

      {dirty ? (
        <Alert tone="warning" title="Unsaved changes">
          Save your profile before leaving this page.
        </Alert>
      ) : null}

      <EmailVerificationBanner className="max-w-2xl" />

      <div className="space-y-6">
        <Card className="max-w-2xl space-y-5">
          <SectionHeader
            eyebrow="Profile"
            title="Your details"
            description="One photo and username for your Fan Card, Host Legacy, messages, and tickets."
          />
          <form onSubmit={(e) => void onSave(e)} className="space-y-4">
            <ImageUrlOrUploadField
              label="Profile photo"
              hint="Same photo on Fan Passport, Host Legacy, and messages. JPEG, PNG, WebP, or GIF — SVG is not allowed."
              value={avatarUrl}
              onChange={(url) => setDraftAvatar(url)}
              mediaType="avatar"
              accountAvatar
              previewClassName="h-20 w-20 rounded-full"
              previewEmptyLabel="No photo"
            />
            <Input
              label="Display name"
              value={displayName}
              onChange={(e) => setDraftDisplayName(e.target.value)}
              required
            />
            <Input
              label="Username"
              value={username}
              onChange={(e) =>
                setDraftUsername(e.target.value.toLowerCase().replace(/^@/, ""))
              }
              hint="Same on your Fan Card (/f/username) and Host Legacy (/@username). 3–32 characters: lowercase letters, numbers, underscore."
              required
            />
            <Button
              type="submit"
              disabled={busy || !dirty || !displayName.trim() || !username.trim()}
            >
              {busy ? "Saving…" : "Save profile"}
            </Button>
          </form>
        </Card>

        <AccountSecurityCard email={email} onEmailChanged={refreshUser} />

        <div className="max-w-2xl">
          <ThemeAppearanceCard />
        </div>

        <NotificationPreferencesSections />
      </div>
    </DashboardShell>
  );
}
