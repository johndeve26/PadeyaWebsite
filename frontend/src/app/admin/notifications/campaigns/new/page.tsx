"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AdminNotificationsNav } from "@/components/admin/AdminNotificationsNav";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
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
  createAdminNotificationCampaign,
  previewAdminNotificationAudience,
  searchAdminNotificationUsers,
  sendAdminNotificationCampaign,
  testAdminNotificationCampaign,
  type NotificationUserHit,
} from "@/lib/admin-notifications/api";
import { ApiError } from "@/lib/api";

export default function AdminNewNotificationCampaignPage() {
  const router = useRouter();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [ctaText, setCtaText] = useState("");
  const [ctaUrl, setCtaUrl] = useState("/dashboard/notifications");
  const [inApp, setInApp] = useState(true);
  const [push, setPush] = useState(true);
  const [email, setEmail] = useState(false);
  const [audienceMode, setAudienceMode] = useState("selected_users");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<NotificationUserHit[]>([]);
  const [selected, setSelected] = useState<NotificationUserHit[]>([]);
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSearch() {
    setError(null);
    try {
      setHits(await searchAdminNotificationUsers(query));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed");
    }
  }

  async function onPreview() {
    setError(null);
    try {
      const res = await previewAdminNotificationAudience({
        audience_mode: audienceMode,
        user_ids: selected.map((u) => u.id),
        audience_filters:
          audienceMode === "selected_users"
            ? { user_ids: selected.map((u) => u.id) }
            : {},
      });
      setPreviewCount(res.count);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Preview failed");
    }
  }

  function toggleUser(user: NotificationUserHit) {
    setSelected((prev) =>
      prev.some((u) => u.id === user.id)
        ? prev.filter((u) => u.id !== user.id)
        : [...prev, user],
    );
  }

  async function saveAndMaybeSend(send: boolean, testOnly = false) {
    setBusy(true);
    setError(null);
    try {
      const campaign = await createAdminNotificationCampaign({
        title,
        body,
        cta_text: ctaText || null,
        cta_url: ctaUrl || null,
        channels: { in_app: inApp, push, email },
        audience_mode: audienceMode,
        user_ids: selected.map((u) => u.id),
        audience_filters:
          audienceMode === "selected_users"
            ? { user_ids: selected.map((u) => u.id) }
            : {},
      });
      if (testOnly) {
        await testAdminNotificationCampaign(campaign.id);
        toast.push({ tone: "success", title: "Test sent to you" });
        router.push(`/admin/notifications/campaigns/${campaign.id}`);
        return;
      }
      if (send) {
        await sendAdminNotificationCampaign(campaign.id);
        toast.push({ tone: "success", title: "Campaign sent" });
      } else {
        toast.push({ tone: "success", title: "Draft saved" });
      }
      router.push(`/admin/notifications/campaigns/${campaign.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save campaign");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin · Notifications"
        title="New campaign"
        description="Compose a custom notification. CTA URLs must be same-origin paths."
        actions={
          <Link href="/admin/notifications/campaigns">
            <Button size="sm" variant="secondary">
              Cancel
            </Button>
          </Link>
        }
      >
        <AdminNotificationsNav />
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="space-y-4 p-5">
            <Input
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={160}
            />
            <Textarea
              label="Message"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={500}
              rows={5}
            />
            <Input
              label="CTA text (optional)"
              value={ctaText}
              onChange={(e) => setCtaText(e.target.value)}
            />
            <Input
              label="CTA path"
              value={ctaUrl}
              onChange={(e) => setCtaUrl(e.target.value)}
              hint="Same-origin only, e.g. /dashboard/notifications"
            />
            <div className="flex flex-wrap gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={inApp}
                  onChange={(e) => setInApp(e.target.checked)}
                />
                In-app
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={push}
                  onChange={(e) => setPush(e.target.checked)}
                />
                Push
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={email}
                  onChange={(e) => setEmail(e.target.checked)}
                />
                Email
              </label>
            </div>
            <Select
              label="Audience"
              value={audienceMode}
              onChange={(e) => setAudienceMode(e.target.value)}
            >
              <option value="selected_users">Selected users</option>
              <option value="all_users">All users</option>
              <option value="role">By role (use filters later)</option>
              <option value="host_followers">Host followers</option>
              <option value="past_buyers">Past buyers</option>
              <option value="vault_members">Vault members</option>
              <option value="ambassadors">Ambassadors</option>
            </Select>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={busy || !title.trim() || !body.trim()}
                onClick={() => void saveAndMaybeSend(false)}
              >
                Save draft
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={busy || !title.trim() || !body.trim()}
                onClick={() => void saveAndMaybeSend(false, true)}
              >
                Test to me
              </Button>
              <Button
                type="button"
                disabled={busy || !title.trim() || !body.trim()}
                onClick={() => void saveAndMaybeSend(true)}
              >
                Send now
              </Button>
            </div>
          </Card>

          <Card className="space-y-4 p-5">
            <h3 className="font-bold text-foreground">Recipients</h3>
            <div className="flex gap-2">
              <Input
                label="Search users"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Name or email"
              />
              <div className="flex items-end">
                <Button type="button" variant="secondary" onClick={() => void onSearch()}>
                  Search
                </Button>
              </div>
            </div>
            <ul className="max-h-48 space-y-1 overflow-auto text-sm">
              {hits.map((u) => (
                <li key={u.id}>
                  <button
                    type="button"
                    className="w-full rounded px-2 py-1 text-left hover:bg-surface-muted"
                    onClick={() => toggleUser(u)}
                  >
                    {selected.some((s) => s.id === u.id) ? "✓ " : ""}
                    {u.full_name} · {u.email}
                  </button>
                </li>
              ))}
            </ul>
            <p className="text-sm text-muted-foreground">
              Selected: {selected.length}
              {previewCount != null ? ` · Preview count: ${previewCount}` : ""}
            </p>
            <Button type="button" variant="secondary" onClick={() => void onPreview()}>
              Preview count
            </Button>
          </Card>
        </div>
      </DashboardShell>
    </RequireAuth>
  );
}
