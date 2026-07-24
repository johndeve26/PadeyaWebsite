import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

import ConnectLayoutClient from "./ConnectLayoutClient";

export const metadata: Metadata = privateAreaMetadata("Fan Connect");

export default function ConnectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ConnectLayoutClient>{children}</ConnectLayoutClient>;
}
