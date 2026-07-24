"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { FanPassportBioAIAssist } from "@/components/passport/FanPassportBioAIAssist";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import {
  Alert,
  Button,
  Card,
  Input,
  Select,
  Textarea,
  useToast,
} from "@/components/ui";
import {
  trackFanDirectoryOptIn,
  trackFanDirectoryOptOut,
} from "@/lib/analytics";
import { ApiError } from "@/lib/api";
import { useUnsavedChanges } from "@/lib/hooks/useUnsavedChanges";
import {
  fetchPassportSettings,
  updatePassportSettings,
} from "@/lib/passport-api";
import type {
  PassportSettings,
  PassportVisibility,
} from "@/lib/types/passport";

const VISIBILITY_OPTIONS: { value: PassportVisibility; label: string }[] = [
  { value: "private", label: "Private — only you" },
  { value: "unlisted", label: "Unlisted — anyone with the link" },
  { value: "public", label: "Public — shareable Fan Passport" },
];

type BoolKey =
  | "show_attended_events"
  | "show_badges"
  | "show_followed_hosts"
  | "show_reviews"
  | "show_vault_unlocks"
  | "show_city_category_stats"
  | "hide_private_events_always";

const TOGGLES: { key: BoolKey; label: string; hint: string }[] = [
  {
    key: "show_attended_events",
    label: "Show attended events",
    hint: "Public nights you checked in to (privacy-safe only).",
  },
  {
    key: "show_badges",
    label: "Show badges",
    hint: "Display earned Fan Passport badges.",
  },
  {
    key: "show_followed_hosts",
    label: "Show followed hosts",
    hint: "Link to Host Legacy Pages you follow.",
  },
  {
    key: "show_reviews",
    label: "Show reviews",
    hint: "Verified reviews you wrote (no private event details).",
  },
  {
    key: "show_vault_unlocks",
    label: "Show Vault unlocks",
    hint: "Titles of unlocks only — never locked content.",
  },
  {
    key: "show_city_category_stats",
    label: "Show city & category stats",
    hint: "Favorite cities and scenes on your public Passport.",
  },
  {
    key: "hide_private_events_always",
    label: "Always hide private / secret events",
    hint: "Recommended. Keeps invite-only and secret-location nights off public view.",
  },
];

export default function PassportSettingsPage() {
  const toast = useToast();
  const { isImpersonating } = useAuth();
  const [settings, setSettings] = useState<PassportSettings | null>(null);
  const [draft, setDraft] = useState<PassportSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [aiNotes, setAiNotes] = useState("");

  const dirty =
    !!settings &&
    !!draft &&
    JSON.stringify(settings) !== JSON.stringify(draft);
  useUnsavedChanges(dirty && !isImpersonating);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const data = await fetchPassportSettings();
        if (!alive) return;
        setSettings(data);
        setDraft(data);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load settings",
          );
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!draft || isImpersonating) return;
    setBusy(true);
    setError(null);
    try {
      const prevDir = settings?.appear_in_directory;
      const saved = await updatePassportSettings({
        username: draft.username,
        display_name: draft.display_name,
        avatar_url: draft.avatar_url,
        tagline: draft.tagline,
        bio: draft.bio,
        visibility: draft.visibility,
        appear_in_directory: draft.appear_in_directory,
        show_attended_events: draft.show_attended_events,
        show_badges: draft.show_badges,
        show_followed_hosts: draft.show_followed_hosts,
        show_reviews: draft.show_reviews,
        show_vault_unlocks: draft.show_vault_unlocks,
        show_city_category_stats: draft.show_city_category_stats,
        hide_private_events_always: draft.hide_private_events_always,
      });
      if (prevDir === false && saved.appear_in_directory) {
        trackFanDirectoryOptIn();
      } else if (prevDir === true && !saved.appear_in_directory) {
        trackFanDirectoryOptOut();
      }
      setSettings(saved);
      setDraft(saved);
      toast.push({ tone: "success", title: "Fan Passport settings saved" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Fan Passport"
      title="Passport settings"
      description="Your Fan Passport starts public and listed in the Fans directory. Untick anytime to go private or leave the directory."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/fans">
            <Button variant="ghost">Fan Directory</Button>
          </Link>
          <Link href="/dashboard/passport">
            <Button variant="secondary">Back to Passport</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not save">
          {error}
        </Alert>
      ) : null}
      {isImpersonating ? (
        <Alert tone="warning" title="Impersonation — privacy settings disabled">
          Passport privacy and directory settings cannot be changed during an
          audited impersonation session.
        </Alert>
      ) : null}
      {dirty && !isImpersonating ? (
        <Alert tone="warning" title="Unsaved changes">
          Save before leaving this page.
        </Alert>
      ) : null}

      {!draft ? (
        <p className="text-sm text-muted-foreground">Loading settings…</p>
      ) : (
        <form
          onSubmit={(e) => void onSave(e)}
          className="space-y-5"
          data-impersonation-locked={isImpersonating ? "true" : "false"}
        >
          <fieldset disabled={isImpersonating} className="space-y-5 disabled:opacity-70">
          <Card className="space-y-4">
            <h3 className="text-lg font-extrabold text-foreground">
              Public discovery
            </h3>
            <p className="text-sm text-muted-foreground">
              There is no forced global list of every fan. Passports marked
              public and listed appear on{" "}
              <Link href="/fans" className="font-semibold underline-offset-2 hover:underline">
                /fans
              </Link>
              {" "}
              — you can leave the directory anytime.
            </p>
            <Select
              label="Profile visibility"
              value={draft.visibility}
              onChange={(e) => {
                const visibility = e.target.value as PassportVisibility;
                setDraft({
                  ...draft,
                  visibility,
                  // Directory listing only applies when Public.
                  appear_in_directory:
                    visibility === "public"
                      ? draft.appear_in_directory
                      : false,
                });
              }}
            >
              {VISIBILITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <label className="flex items-start justify-between gap-4 rounded-[var(--radius-md)] border border-border px-4 py-3">
              <div>
                <p className="font-semibold text-foreground">
                  Show my Fan Passport in the public directory
                </p>
                <p className="text-sm text-muted-foreground">
                  Requires Public visibility. Unlisted and private never appear
                  on /fans.
                </p>
              </div>
              <input
                type="checkbox"
                className="mt-1 h-5 w-5 accent-[var(--brand-green)]"
                checked={draft.appear_in_directory}
                disabled={draft.visibility !== "public"}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    appear_in_directory: e.target.checked,
                  })
                }
              />
            </label>
            <Input
              label="Public username"
              value={draft.username || ""}
              onChange={(e) =>
                setDraft({ ...draft, username: e.target.value.toLowerCase() })
              }
              hint="3–32 characters. Used in /f/username when public or unlisted."
            />
            <Input
              label="Public display name"
              value={draft.display_name}
              onChange={(e) =>
                setDraft({ ...draft, display_name: e.target.value })
              }
            />
            <ImageUrlOrUploadField
              label="Public avatar"
              hint="Optional profile photo. Host accounts can upload; others can paste a URL."
              value={draft.avatar_url || ""}
              onChange={(url) =>
                setDraft({ ...draft, avatar_url: url.trim() || null })
              }
              mediaType="other"
              previewClassName="h-16 w-16 rounded-full"
            />
            <Input
              label="Public tagline"
              value={draft.tagline || ""}
              onChange={(e) =>
                setDraft({ ...draft, tagline: e.target.value || null })
              }
            />
            <FanPassportBioAIAssist
              bio={draft.bio || ""}
              aiNotes={aiNotes}
              disabled={isImpersonating}
              onApply={(text) => setDraft({ ...draft, bio: text })}
            />
            <Textarea
              label="Notes for AI (optional)"
              value={aiNotes}
              onChange={(e) => setAiNotes(e.target.value)}
              hint="Tone, scenes, or what to highlight — not private attendance or spend."
              className="min-h-[72px]"
            />
            <Textarea
              label="Bio"
              value={draft.bio || ""}
              onChange={(e) =>
                setDraft({ ...draft, bio: e.target.value || null })
              }
            />
            {draft.share_path && draft.visibility !== "private" ? (
              <div className="space-y-2 rounded-[var(--radius-md)] border border-primary/25 bg-primary/5 px-4 py-3">
                <p className="text-sm text-muted-foreground">
                  Share link:{" "}
                  <Link
                    href={draft.share_path}
                    className="font-semibold text-foreground underline-offset-2 hover:underline"
                  >
                    {draft.share_path}
                  </Link>
                </p>
                <Link href={draft.share_path} target="_blank" rel="noreferrer">
                  <Button size="sm" variant="secondary" type="button">
                    View public Passport
                  </Button>
                </Link>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Private Passports are never listed or reachable at /f/username.
                Set visibility to Public or Unlisted, then save.
              </p>
            )}
          </Card>

          <Card className="space-y-4">
            <h3 className="text-lg font-extrabold text-foreground">
              What others can see
            </h3>
            <ul className="space-y-3">
              {TOGGLES.map((toggle) => (
                <li
                  key={toggle.key}
                  className="flex items-start justify-between gap-4 rounded-[var(--radius-md)] border border-border px-4 py-3"
                >
                  <div>
                    <p className="font-semibold text-foreground">
                      {toggle.label}
                    </p>
                    <p className="text-sm text-muted-foreground">{toggle.hint}</p>
                  </div>
                  <input
                    type="checkbox"
                    className="mt-1 h-5 w-5 accent-[var(--brand-green)]"
                    checked={draft[toggle.key]}
                    onChange={(e) =>
                      setDraft({ ...draft, [toggle.key]: e.target.checked })
                    }
                  />
                </li>
              ))}
            </ul>
          </Card>

          <div className="flex flex-wrap gap-3">
            <Button
              type="submit"
              size="lg"
              disabled={busy || !dirty || isImpersonating}
            >
              {busy ? "Saving…" : "Save Passport settings"}
            </Button>
            <Link href="/dashboard/passport">
              <Button type="button" variant="secondary" size="lg">
                Cancel
              </Button>
            </Link>
          </div>
          </fieldset>
        </form>
      )}
    </DashboardShell>
  );
}
