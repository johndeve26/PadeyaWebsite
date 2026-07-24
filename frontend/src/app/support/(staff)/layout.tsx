import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

import SupportStaffLayoutClient from "./SupportStaffLayoutClient";

export const metadata: Metadata = privateAreaMetadata("Support desk");

export default function SupportStaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SupportStaffLayoutClient>{children}</SupportStaffLayoutClient>;
}
