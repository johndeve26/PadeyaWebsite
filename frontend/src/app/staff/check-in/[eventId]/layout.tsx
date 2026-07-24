"use client";

import { RequireAuth } from "@/components/auth/RequireAuth";

export default function StaffCheckInLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RequireAuth roles={["host", "host_staff", "super_admin"]}>{children}</RequireAuth>
  );
}
