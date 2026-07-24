import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

import SponsorLayoutClient from "./SponsorLayoutClient";

export const metadata: Metadata = privateAreaMetadata("Sponsor");

export default function SponsorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SponsorLayoutClient>{children}</SponsorLayoutClient>;
}
