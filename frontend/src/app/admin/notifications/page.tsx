"use client";

import Link from "next/link";

import { AdminNotificationsNav } from "@/components/admin/AdminNotificationsNav";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, Card } from "@/components/ui";

export default function AdminNotificationsHubPage() {
  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin"
        title="Notifications"
        description="Control platform notification types, templates, and custom campaigns."
        actions={
          <Link href="/admin/audit-logs">
            <Button variant="secondary" size="sm">
              Audit
            </Button>
          </Link>
        }
      >
        <AdminNotificationsNav />
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="space-y-3 p-5">
            <h2 className="font-bold text-foreground">Type settings</h2>
            <p className="text-sm text-muted-foreground">
              Enable or disable each event, channels, audience, and cooldowns.
            </p>
            <Link href="/admin/notifications/settings">
              <Button>Open settings</Button>
            </Link>
          </Card>
          <Card className="space-y-3 p-5">
            <h2 className="font-bold text-foreground">Campaigns</h2>
            <p className="text-sm text-muted-foreground">
              Compose custom notifications to selected users or audiences.
            </p>
            <div className="flex flex-wrap gap-2">
              <Link href="/admin/notifications/campaigns">
                <Button>View campaigns</Button>
              </Link>
              <Link href="/admin/notifications/campaigns/new">
                <Button variant="secondary">New campaign</Button>
              </Link>
            </div>
          </Card>
          <Card className="space-y-3 p-5">
            <h2 className="font-bold text-foreground">Templates</h2>
            <p className="text-sm text-muted-foreground">
              Manage title/body templates used by typed notifications.
            </p>
            <Link href="/admin/notifications/templates">
              <Button>Manage templates</Button>
            </Link>
          </Card>
        </div>
      </DashboardShell>
    </RequireAuth>
  );
}
