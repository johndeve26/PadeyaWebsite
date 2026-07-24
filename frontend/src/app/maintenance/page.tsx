"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { brand } from "@/lib/brand";
import {
  fetchPublicMaintenanceStatus,
  type PublicMaintenanceStatus,
} from "@/lib/maintenance-api";

export default function PublicMaintenancePage() {
  const [status, setStatus] = useState<PublicMaintenanceStatus | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setStatus(await fetchPublicMaintenanceStatus());
      } catch {
        setStatus({
          mode: "active",
          maintenance: true,
          title: "Maintenance",
          message: "Pàdéyá is undergoing maintenance. We’ll be back soon.",
        });
      }
    })();
  }, []);

  const title = status?.title || "Maintenance";
  const message =
    status?.message || "Pàdéyá is undergoing maintenance. We’ll be back soon.";

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-16 text-center">
      <p className="mb-10 font-display text-2xl font-extrabold tracking-tight text-heading">
        {brand.name}
      </p>
      <h1 className="font-display text-3xl font-bold tracking-tight text-heading sm:text-4xl">
        {title}
      </h1>
      <p className="mt-4 max-w-md text-base leading-relaxed text-muted-foreground">
        {message}
      </p>
      {status?.expected_back_at ? (
        <p className="mt-3 text-sm text-muted-foreground">
          Expected back: {new Date(status.expected_back_at).toLocaleString()}
        </p>
      ) : null}
      <Link
        href="/"
        className="mt-10 text-sm font-semibold text-primary underline-offset-4 hover:underline"
      >
        Try homepage
      </Link>
    </main>
  );
}
