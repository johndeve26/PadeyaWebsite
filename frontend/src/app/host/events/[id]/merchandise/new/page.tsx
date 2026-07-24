"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { RequireHost } from "@/components/hosts/RequireHost";
import { EventOpsNav } from "@/components/host/EventOpsNav";
import { EventMerchSubnav } from "@/components/merch/host/EventMerchSubnav";
import { HostMerchProductForm } from "@/components/merch/host/HostMerchProductForm";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Breadcrumb, Button } from "@/components/ui";

export default function EventMerchandiseNewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Add merch product"
        description="Create official merch for your event, storefront, Vault, or post-event drop."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/merchandise">
              <Button variant="secondary" size="sm">
                All merch
              </Button>
            </Link>
            <Link href={`/host/events/${params.id}/merchandise`}>
              <Button variant="secondary" size="sm">
                Studio home
              </Button>
            </Link>
          </div>
        }
      >
        <EventOpsNav eventId={params.id} />
        <EventMerchSubnav eventId={params.id} />
        <Breadcrumb
          items={[
            { label: "Host", href: "/host" },
            { label: "Merchandise", href: "/host/merchandise" },
            { label: "New product" },
          ]}
        />
        <div className="mx-auto w-full max-w-6xl">
          <HostMerchProductForm
            eventId={params.id}
            studio
            onSaved={(product) => {
              router.push(
                `/host/events/${params.id}/merchandise/${product.id}/edit`,
              );
            }}
          />
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
