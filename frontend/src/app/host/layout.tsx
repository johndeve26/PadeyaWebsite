import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

import HostLayoutClient from "./HostLayoutClient";

export const metadata: Metadata = privateAreaMetadata("Host");

export default function HostLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <HostLayoutClient>{children}</HostLayoutClient>;
}
