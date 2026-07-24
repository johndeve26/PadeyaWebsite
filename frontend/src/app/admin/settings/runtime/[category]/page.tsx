"use client";

import { useParams } from "next/navigation";

import { RuntimeSettingsCategoryPage } from "@/components/admin/runtime-settings";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { formatCategoryLabel } from "@/lib/runtime-settings-display";

export default function AdminRuntimeSettingsCategoryRoute() {
  const params = useParams();
  const category = String(params.category ?? "");

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Runtime settings"
      title={formatCategoryLabel(category)}
      description="Fields render from API registry metadata — not a hard-coded form list."
    >
      <RuntimeSettingsCategoryPage category={category} />
    </DashboardShell>
  );
}
