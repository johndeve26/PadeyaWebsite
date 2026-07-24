import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

import DashboardLayoutClient from "./DashboardLayoutClient";

export const metadata: Metadata = privateAreaMetadata("Personal");

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DashboardLayoutClient>{children}</DashboardLayoutClient>;
}
