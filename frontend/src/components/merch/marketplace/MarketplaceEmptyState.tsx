"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Button, EmptyState } from "@/components/ui";

type Props = {
  title?: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export function MarketplaceEmptyState({
  title = "No merch available yet.",
  description = "When hosts publish shop products, event add-ons, drops, or Vault exclusives, they will appear here.",
  action,
  className,
}: Props) {
  return (
    <EmptyState
      className={className}
      title={title}
      description={description}
      action={
        action ?? (
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Link href="/events">
              <Button variant="secondary" size="sm">
                Browse events
              </Button>
            </Link>
            <Link href="/host/merchandise/new">
              <Button size="sm">Create merch as host</Button>
            </Link>
          </div>
        )
      }
    />
  );
}
