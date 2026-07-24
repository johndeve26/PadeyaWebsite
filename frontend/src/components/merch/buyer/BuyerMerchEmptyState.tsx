import Link from "next/link";

import { Button, EmptyState } from "@/components/ui";
import type { MerchWalletTab } from "@/lib/merch/buyer-merch-wallet";

const COPY: Record<
  MerchWalletTab,
  { title: string; description: string; cta: string }
> = {
  ready: {
    title: "No merch is ready for pickup right now",
    description: "When a host marks your order ready, the pickup QR will appear here.",
    cta: "Browse events",
  },
  shipping: {
    title: "Nothing in progress",
    description: "Shipping, delivery, and processing orders will show up here.",
    cta: "Browse events",
  },
  completed: {
    title: "No picked up or delivered merch",
    description: "Completed merch orders will appear here.",
    cta: "Browse events",
  },
  cancelled: {
    title: "No cancelled or refunded merch",
    description: "Cancelled and refunded items stay here for your records.",
    cta: "Browse events",
  },
  all: {
    title: "No merch orders yet",
    description: "Official event merch you buy on Pàdéyá will appear here.",
    cta: "Browse events",
  },
};

export function BuyerMerchEmptyState({ tab }: { tab: MerchWalletTab }) {
  const copy = COPY[tab];
  return (
    <EmptyState
      title={copy.title}
      description={copy.description}
      action={
        <Link href="/events">
          <Button size="lg">{copy.cta}</Button>
        </Link>
      }
    />
  );
}
