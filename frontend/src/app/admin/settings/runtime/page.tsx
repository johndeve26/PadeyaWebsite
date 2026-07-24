"use client";

import Link from "next/link";

import { RuntimeSettingsDashboard } from "@/components/admin/runtime-settings";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";

export default function AdminRuntimeSettingsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Runtime settings"
      description="Optional integration and worker knobs with env fallback. Boot-critical secrets stay out of this UI."
      actions={
        <Link href="/admin/settings/runtime/audit">
          <Button variant="secondary" size="sm">
            Audit
          </Button>
        </Link>
      }
    >
      <RuntimeSettingsDashboard />
    </DashboardShell>
  );
}
