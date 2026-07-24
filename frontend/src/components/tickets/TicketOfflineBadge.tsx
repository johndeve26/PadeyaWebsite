import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import { readCachedTicket } from "@/lib/pwa/offline-ticket-cache";

export function TicketOfflineBadge({
  ticketId,
  className = "",
}: {
  ticketId: string;
  className?: string;
}) {
  const cached = Boolean(readCachedTicket(ticketId));
  if (!cached) return null;

  return (
    <Badge
      tone="outline"
      size="sm"
      className={cn("font-semibold normal-case tracking-normal", className)}
    >
      Saved offline
    </Badge>
  );
}

export function TicketOfflineHint({ className = "" }: { className?: string }) {
  return (
    <p className={cn("text-sm text-muted-foreground", className)}>
      Cached copies stay available offline.
    </p>
  );
}
