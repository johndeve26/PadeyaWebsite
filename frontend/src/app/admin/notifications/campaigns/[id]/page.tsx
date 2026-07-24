"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AdminNotificationsNav } from "@/components/admin/AdminNotificationsNav";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  DataTable,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  fetchAdminCampaignDeliveries,
  fetchAdminNotificationCampaigns,
  sendAdminNotificationCampaign,
  testAdminNotificationCampaign,
  type AdminNotificationCampaign,
  type CampaignDelivery,
} from "@/lib/admin-notifications/api";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

export default function AdminNotificationCampaignDetailPage() {
  const params = useParams();
  const id = String(params.id ?? "");
  const toast = useToast();
  const [campaign, setCampaign] = useState<AdminNotificationCampaign | null>(
    null,
  );
  const [deliveries, setDeliveries] = useState<CampaignDelivery[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const all = await fetchAdminNotificationCampaigns();
      setCampaign(all.find((c) => c.id === id) ?? null);
      setDeliveries(await fetchAdminCampaignDeliveries(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load");
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void load();
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  async function onSend() {
    setBusy(true);
    try {
      await sendAdminNotificationCampaign(id);
      toast.push({ tone: "success", title: "Campaign sent" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Send failed");
    } finally {
      setBusy(false);
    }
  }

  async function onTest() {
    setBusy(true);
    try {
      await testAdminNotificationCampaign(id);
      toast.push({ tone: "success", title: "Test sent" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Test failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin · Notifications"
        title={campaign?.title || "Campaign"}
        description="Delivery status for this custom notification."
        actions={
          <Link href="/admin/notifications/campaigns">
            <Button size="sm" variant="secondary">
              Back
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
        {!campaign ? (
          <SkeletonLoader lines={4} />
        ) : (
          <div className="space-y-4">
            <Card className="space-y-3 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="neutral">{campaign.status}</Badge>
                <span className="text-sm text-muted-foreground">
                  {campaign.recipient_count} recipients · {campaign.audience_mode}
                </span>
              </div>
              <p className="text-sm text-foreground">{campaign.body}</p>
              <p className="text-xs text-muted-foreground">
                Channels:{" "}
                {[
                  campaign.channels.in_app ? "in-app" : null,
                  campaign.channels.push ? "push" : null,
                  campaign.channels.email ? "email" : null,
                ]
                  .filter(Boolean)
                  .join(", ") || "none"}
                {campaign.sent_at
                  ? ` · sent ${formatDateTime(campaign.sent_at)}`
                  : ""}
              </p>
              <div className="flex flex-wrap gap-2">
                {campaign.status === "draft" || campaign.status === "scheduled" ? (
                  <Button disabled={busy} onClick={() => void onSend()}>
                    Send now
                  </Button>
                ) : null}
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void onTest()}
                >
                  Test to me
                </Button>
              </div>
            </Card>

            <Card className="p-5">
              <h3 className="mb-3 font-bold text-foreground">Deliveries</h3>
              <DataTable
                columns={[
                  {
                    key: "channel",
                    header: "Channel",
                    primary: true,
                    cell: (d) => d.channel,
                  },
                  {
                    key: "status",
                    header: "Status",
                    cell: (d) => d.status,
                  },
                  {
                    key: "recipient_user_id",
                    header: "User",
                    cell: (d) => d.recipient_user_id.slice(0, 8),
                  },
                  {
                    key: "error_reason",
                    header: "Error",
                    cell: (d) => d.error_reason || "—",
                  },
                  {
                    key: "created_at",
                    header: "When",
                    cell: (d) => formatDateTime(d.created_at),
                  },
                ]}
                rows={deliveries}
                rowKey={(d) => d.id}
                emptyTitle="No deliveries yet."
              />
            </Card>
          </div>
        )}
      </DashboardShell>
    </RequireAuth>
  );
}
