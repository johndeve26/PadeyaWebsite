import Link from "next/link";

import { Button, EmptyState } from "@/components/ui";

export function EmptyMessagesState({
  title = "No messages yet",
  description = "Message hosts from Legacy Pages or event pages — conversations stay on Pàdéyá.",
  ctaHref = "/hosts",
  ctaLabel = "Discover hosts",
}: {
  title?: string;
  description?: string;
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <EmptyState
      title={title}
      description={description}
      action={
        <Link href={ctaHref}>
          <Button>{ctaLabel}</Button>
        </Link>
      }
    />
  );
}
