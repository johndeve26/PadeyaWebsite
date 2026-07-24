import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

import AdminLayoutClient from "./AdminLayoutClient";

export const metadata: Metadata = privateAreaMetadata("Admin");

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AdminLayoutClient>{children}</AdminLayoutClient>;
}
