"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
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

export default function HostMerchandiseEditPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [product, setProduct] = useState<MerchProduct | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchHostMerchProduct(params.id);
        if (active) setProduct(row);
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
  }, [params.id]);

  if (error && !product) {
    return (
      <RequireHost>
        <DashboardShell
          tone="soft"
          eyebrow="Merch Studio"
          title="Unavailable"
          description="This product could not be loaded."
        >
          <EmptyState
            title="Product not found"
            description={error}
            action={
              <Link href="/host/merchandise">
                <Button variant="secondary">All merch</Button>
              </Link>
            }
          />
        </DashboardShell>
      </RequireHost>
    );
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title={product?.name ?? "Edit product"}
        description={
          product?.event_title
            ? `Linked to ${product.event_title}`
            : "Update price, stock, and pickup instructions."
        }
        actions={
          <div className="flex flex-wrap gap-2">
            {product ? (
              <Link
                href={`/host/events/${product.event_id}/merchandise`}
              >
                <Button variant="secondary" size="sm">
                  Event catalog
                </Button>
              </Link>
            ) : null}
            <Link href="/host/merchandise">
              <Button variant="secondary" size="sm">
                All merch
              </Button>
            </Link>
          </div>
        }
      >
        <div className="mx-auto w-full max-w-6xl space-y-4">
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
                eventId={product.event_id}
                studio
                submitLabel="Save product"
                onSaved={() => {
                  router.push(`/host/events/${product.event_id}/merchandise`);
                }}
              />
            </>
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
