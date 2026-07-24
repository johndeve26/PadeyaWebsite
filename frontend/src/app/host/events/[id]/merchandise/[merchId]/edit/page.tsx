"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { EventOpsNav } from "@/components/host/EventOpsNav";
import { EventMerchSubnav } from "@/components/merch/host/EventMerchSubnav";
import { HostMerchProductForm } from "@/components/merch/host/HostMerchProductForm";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchHostMerchProduct } from "@/lib/merch-api";
import type { MerchProduct } from "@/lib/types/merch";

export default function EventMerchandiseEditPage() {
  const params = useParams<{ id: string; merchId: string }>();
  const router = useRouter();
  const [product, setProduct] = useState<MerchProduct | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchHostMerchProduct(params.merchId, params.id);
        if (!active) return;
        if (row.event_id !== params.id) {
          setError("This product belongs to a different event.");
          return;
        }
        setProduct(row);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Product not found",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id, params.merchId]);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title={product?.name ?? "Edit product"}
        description="Basic info, images, pricing, variants, sales rules, pickup, and live preview."
        actions={
          <Link href={`/host/events/${params.id}/merchandise`}>
            <Button variant="secondary" size="sm">
              Studio home
            </Button>
          </Link>
        }
      >
        <EventOpsNav eventId={params.id} />
        <EventMerchSubnav eventId={params.id} />
        {error && !product ? (
          <EmptyState
            title="Product not found"
            description={error}
            action={
              <Link href={`/host/events/${params.id}/merchandise`}>
                <Button variant="secondary">Back to studio</Button>
              </Link>
            }
          />
        ) : (
          <div className="mx-auto w-full max-w-6xl space-y-4">
            {error ? (
              <Alert tone="danger" title="Merch error">
                {error}
              </Alert>
            ) : null}
            {!product ? (
              <SkeletonLoader lines={6} />
            ) : (
              <>
                {product.moderation_status === "hidden" ||
                product.moderation_status === "removed" ? (
                  <Alert
                    tone="warning"
                    title={
                      product.moderation_status === "hidden"
                        ? "Hidden by Pàdéyá moderation"
                        : "Removed by Pàdéyá moderation"
                    }
                  >
                    This listing is not shown publicly and cannot be purchased.
                    {product.moderation_note
                      ? ` Reason: ${product.moderation_note}`
                      : " An admin must restore it before you can reactivate sales."}
                  </Alert>
                ) : null}
                <HostMerchProductForm
                  product={product}
                  eventId={params.id}
                  studio
                  submitLabel="Save product"
                  onSaved={() => {
                    router.push(`/host/events/${params.id}/merchandise`);
                  }}
                />
              </>
            )}
          </div>
        )}
      </DashboardShell>
    </RequireHost>
  );
}
