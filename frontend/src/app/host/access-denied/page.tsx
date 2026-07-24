"use client";

import { HostPermissionDenied } from "@/components/hosts/HostPermissionDenied";
import { RequireHost } from "@/components/hosts/RequireHost";

export default function HostAccessDeniedPage() {
  return (
    <RequireHost>
      <HostPermissionDenied />
    </RequireHost>
  );
}
