import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

import StaffCheckInLayoutClient from "./StaffCheckInLayoutClient";

export const metadata: Metadata = privateAreaMetadata("Staff check-in");

export default function StaffCheckInLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <StaffCheckInLayoutClient>{children}</StaffCheckInLayoutClient>;
}
