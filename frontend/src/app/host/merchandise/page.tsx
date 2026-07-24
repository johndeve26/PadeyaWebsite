"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { HostMerchProductList } from "@/components/merch/host/HostMerchProductList";
import { HostStorefrontSettingsCard } from "@/components/merch/host/HostStorefrontSettingsCard";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAllHostMerchProducts } from "@/lib/merch-api";
import type { MerchProduct } from "@/lib/types/merch";

export default function HostMerchandisePage() {
  const [products, setProducts] = useState<MerchProduct[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const rows = await fetchAllHostMerchProducts();
    setProducts(rows);
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchAllHostMerchProducts();
        if (active) setProducts(rows);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load merchandise",
          );
          setProducts([]);
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
        eyebrow="Operate"
        title="Merch Studio"
        description="Event-linked merch and your host storefront on Pàdéyá."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/merchandise/new">
              <Button size="sm">Add product</Button>
            </Link>
            <Link href="/host/merchandise/orders">
              <Button size="sm" variant="secondary">
                Orders
              </Button>
            </Link>
            <Link href="/host/merchandise/fulfillment">
              <Button size="sm" variant="secondary">
                Fulfillment
              </Button>
            </Link>
            <Link href="/host/events">
              <Button size="sm" variant="secondary">
                Add bundle
              </Button>
            </Link>
            <Link href="/host/merchandise/shipping-zones">
              <Button size="sm" variant="secondary">
                Shipping zones
              </Button>
            </Link>
            <Link href="/host/merchandise/size-charts">
              <Button size="sm" variant="secondary">
                Size charts
              </Button>
            </Link>
            <Link href="/host/merchandise/discounts">
              <Button size="sm" variant="secondary">
                Discount codes
              </Button>
            </Link>
            <Link href="/host/merchandise/revenue">
              <Button size="sm" variant="secondary">
                Revenue report
              </Button>
            </Link>
            <Link href="/host/merchandise/reviews">
              <Button size="sm" variant="secondary">
                Reviews
              </Button>
            </Link>
            <Link href="/host/merchandise/print-on-demand">
              <Button size="sm" variant="secondary">
                Print on demand
              </Button>
            </Link>
            <Link href="/host/merchandise/stock-alerts">
              <Button size="sm" variant="secondary">
                Stock alerts
              </Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Could not load merchandise">
            {error}
          </Alert>
        ) : null}
        <Card className="space-y-4">
          <HostStorefrontSettingsCard />
        </Card>
        <Card className="space-y-4">
          {products === null ? (
            <SkeletonLoader lines={4} />
          ) : (
            <HostMerchProductList
              products={products}
              showEvent
              editHref={(product) => `/host/merchandise/${product.id}/edit`}
              onChanged={load}
            />
          )}
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
