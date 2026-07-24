import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Messages");

export default function MessagesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
