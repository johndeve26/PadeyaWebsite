"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { HostMerchProductForm } from "@/components/merch/host/HostMerchProductForm";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Breadcrumb, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyEvents } from "@/lib/events-api";
import type { EventItem } from "@/lib/types/events";

export default function HostMerchandiseNewPage() {
  const router = useRouter();
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchMyEvents();
        if (active) setEvents(rows);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load events",
          );
          setEvents([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Add merch product"
        description="Create standalone shop merch, or attach a product to an event, Vault, or post-event drop."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/merchandise">
              <Button variant="secondary" size="sm">
                All merch
              </Button>
            </Link>
            <Link href="/merch">
              <Button variant="secondary" size="sm">
                View shop
              </Button>
            </Link>
          </div>
        }
      >
        <Breadcrumb
          items={[
            { label: "Host", href: "/host" },
            { label: "Merchandise", href: "/host/merchandise" },
            { label: "New product" },
          ]}
        />
        {error ? (
          <Alert tone="danger" title="Could not load events">
            {error}
          </Alert>
        ) : null}
        <div className="mx-auto w-full max-w-6xl space-y-4">
          {events === null ? (
            <SkeletonLoader lines={6} />
          ) : (
            <>
              {events.length === 0 ? (
                <Alert tone="info" title="Standalone shop product">
                  You have no events yet. Publish a standalone host-shop
                  product now, or{" "}
                  <Link href="/host/events/new" className="font-bold underline">
                    create an event
                  </Link>{" "}
                  to attach merch later.
                </Alert>
              ) : null}
              <HostMerchProductForm
                studio
                allowStandalone
                eventOptions={events.map((e) => ({
                  id: e.id,
                  title: e.title,
                }))}
                onSaved={(product) => {
                  router.push(`/host/merchandise/${product.id}/edit`);
                }}
              />
            </>
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
