"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AdminNotificationsNav } from "@/components/admin/AdminNotificationsNav";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  fetchAdminNotificationCampaigns,
  type AdminNotificationCampaign,
} from "@/lib/admin-notifications/api";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

export default function AdminNotificationCampaignsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<AdminNotificationCampaign[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRows(await fetchAdminNotificationCampaigns());
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load");
      toast.push({ tone: "danger", title: "Could not load campaigns" });
    }
  }, [toast]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void load();
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin · Notifications"
        title="Campaigns"
        description="Custom admin notifications and delivery status."
        actions={
          <Link href="/admin/notifications/campaigns/new">
            <Button size="sm">New campaign</Button>
          </Link>
        }
      >
        <AdminNotificationsNav />
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}
        {!rows ? (
          <SkeletonLoader lines={4} />
        ) : rows.length === 0 ? (
          <Card className="p-6 text-sm text-muted-foreground">
            No campaigns yet. Create one to notify selected users.
          </Card>
        ) : (
          <div className="space-y-3">
            {rows.map((c) => (
              <Card key={c.id} className="space-y-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-bold text-foreground">{c.title}</h3>
                  <Badge tone="neutral" size="sm">
                    {c.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">{c.body}</p>
                <p className="text-xs text-muted-foreground">
                  {c.recipient_count} recipients · {c.audience_mode}
                  {c.sent_at ? ` · sent ${formatDateTime(c.sent_at)}` : ""}
                </p>
                <div className="flex gap-2">
                  <Link href={`/admin/notifications/campaigns/${c.id}`}>
                    <Button size="sm" variant="secondary">
                      Details
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        )}
      </DashboardShell>
    </RequireAuth>
  );
}
