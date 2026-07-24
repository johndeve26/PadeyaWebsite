import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Team invite");

export default function TeamInviteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
