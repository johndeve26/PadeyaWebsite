import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Staff");

export default function StaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
