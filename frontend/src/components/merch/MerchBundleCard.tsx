"use client";

import Link from "next/link";

import { Badge, Button } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import type { MerchBundle } from "@/lib/types/merch";

type Props = {
  bundle: MerchBundle;
  eventSlug: string;
  referralCode?: string;
};

export function MerchBundleCard({ bundle, eventSlug, referralCode }: Props) {
  const savings = Number(bundle.savings ?? 0);
  const listTotal = Number(bundle.component_list_total ?? 0);
  const included = (bundle.merch_variant_rules ?? [])
    .map((r) => r.product_name || r.variant_label)
    .filter(Boolean)
    .slice(0, 3);
  const href = `/events/${eventSlug}/checkout?bundle=${bundle.id}${
    referralCode ? `&ref=${referralCode}` : ""
  }`;

  return (
    <article className="flex h-full flex-col justify-between rounded-[var(--radius-lg)] border border-border bg-card p-5">
      <div className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          <Badge tone="accent" size="sm">
            Ticket + merch
          </Badge>
          {savings > 0 ? (
            <Badge tone="success" size="sm">
              Save {formatNgn(savings)}
            </Badge>
          ) : null}
        </div>
        <div>
          <h3 className="text-base font-extrabold tracking-tight text-foreground">
            {bundle.name}
          </h3>
          {bundle.description ? (
            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
              {bundle.description}
            </p>
          ) : null}
        </div>
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between gap-2">
            <dt className="text-muted-foreground">Ticket</dt>
            <dd className="font-bold text-foreground">
              {bundle.ticket_type_name || "Event ticket"}
            </dd>
          </div>
          {included.length > 0 ? (
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Includes</dt>
              <dd className="max-w-[60%] text-right font-bold text-foreground">
                {included.join(", ")}
              </dd>
            </div>
          ) : null}
          {listTotal > 0 ? (
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Separate total</dt>
              <dd className="text-muted-foreground line-through">
                {formatNgn(listTotal)}
              </dd>
            </div>
          ) : null}
        </dl>
      </div>
      <div className="mt-5 flex items-center justify-between gap-3">
        <p className="text-lg font-extrabold text-foreground">
          {formatNgn(bundle.bundle_price)}
        </p>
        <Link href={href}>
          <Button size="sm">Select bundle</Button>
        </Link>
      </div>
    </article>
  );
}
