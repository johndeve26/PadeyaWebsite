"use client";

import type { ReactNode } from "react";

/** Workspace provider already wraps the dashboard layout. */
export default function DashboardTeamLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <>{children}</>;
}
