import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Support ticket");

/** Private ticket views — public Support Center stays indexable at /support. */
export default function SupportTicketsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
