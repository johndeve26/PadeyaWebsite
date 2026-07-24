"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button } from "@/components/ui";
import type { MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  product: MerchCatalogProduct;
  hostSlug?: string | null;
  eventSlug?: string | null;
  loginNext?: string;
};

const ACCESS_COPY: Record<string, string> = {
  follower_required: "Follow this host to unlock.",
  ticket_required: "Available to ticket holders for this event.",
  vip_ticket_required: "A VIP ticket unlocks this exclusive merch.",
  check_in_required: "Check in at the event to unlock.",
  vault_locked:
    "Unlock through the host’s Vault to purchase this merch.",
  paid_vault_required:
    "Unlock through the host’s Vault to purchase this merch.",
  invite_required: "Redeem your Vault invite to unlock.",
  vault_login_required: "Sign in to unlock Vault-exclusive merch.",
  login_required: "Sign in to purchase this merch.",
};

export function MerchAccessLockPanel({
  product,
  hostSlug,
  eventSlug,
  loginNext,
}: Props) {
  const [showRequirements, setShowRequirements] = useState(false);
  const locked = Boolean(product.access_locked || product.teaser_only);
  const eligible = Boolean(product.access_eligible);
  if (!locked || eligible) return null;

  const requirements = product.access_requirements ?? [];
  const hint =
    product.unlock_hint ||
    (product.is_vault_exclusive || product.requires_vault_access
      ? ACCESS_COPY.vault_locked
      : null) ||
    (product.requires_ticket
      ? "Available to ticket holders for this event."
      : null) ||
    (product.access_reason
      ? ACCESS_COPY[product.access_reason]
      : null) ||
    "This merch is locked until you meet the access requirements.";
  const vaultHref = hostSlug ? `/@${hostSlug}/vault` : "/vault";
  const eventHref = eventSlug ? `/events/${eventSlug}` : null;
  const loginHref = `/login?next=${encodeURIComponent(
    loginNext || (typeof window !== "undefined" ? window.location.pathname : "/"),
  )}`;
  const needsLogin =
    product.access_reason === "vault_login_required" ||
    product.access_reason === "login_required";

  return (
    <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/60 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="dark" size="sm">
          {product.access_label || "Exclusive"}
        </Badge>
        {product.is_vault_exclusive ? (
          <Badge tone="outline" size="sm">
            Vault exclusive
          </Badge>
        ) : null}
      </div>
      <p className="text-sm text-muted-foreground">{hint}</p>
      <div className="flex flex-wrap gap-2">
        {needsLogin ? (
          <Link href={loginHref}>
            <Button size="sm">Sign in to unlock</Button>
          </Link>
        ) : product.is_vault_exclusive || product.requires_vault_access ? (
          <Link href={vaultHref}>
            <Button size="sm">Explore Vault to unlock</Button>
          </Link>
        ) : product.required_access_type === "follower" ? (
          hostSlug ? (
            <Link href={`/@${hostSlug}`}>
              <Button size="sm">Follow host to unlock</Button>
            </Link>
          ) : null
        ) : eventHref ? (
          <Link href={eventHref}>
            <Button size="sm">View event access</Button>
          </Link>
        ) : null}
        <Button
          size="sm"
          variant="secondary"
          type="button"
          onClick={() => setShowRequirements((v) => !v)}
        >
          {showRequirements ? "Hide access requirements" : "View access requirements"}
        </Button>
      </div>
      {showRequirements ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {requirements.length > 0 ? (
            requirements.map((req) => <li key={req}>{req}</li>)
          ) : (
            <li>Meet the host access rules shown above to purchase.</li>
          )}
        </ul>
      ) : null}
    </div>
  );
}
