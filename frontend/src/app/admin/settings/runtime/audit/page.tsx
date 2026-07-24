"use client";

import Link from "next/link";

import { RuntimeSettingsAuditTable } from "@/components/admin/runtime-settings";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";

export default function AdminRuntimeSettingsAuditPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Runtime settings"
      title="Audit history"
      description="runtime_setting_* actions for updates, clears, and integration tests."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/settings/runtime">
            <Button variant="ghost" size="sm">
              Back to hub
            </Button>
          </Link>
          <Link href="/admin/audit-logs?action=runtime_setting">
            <Button variant="secondary" size="sm">
              Platform audit
            </Button>
          </Link>
        </div>
      }
    >
      <RuntimeSettingsAuditTable />
    </DashboardShell>
  );
}
