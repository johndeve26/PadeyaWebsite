import { Badge } from "@/components/ui";
import type { MerchBadgeTone } from "@/lib/merch/buyer-merch-wallet";

export function MerchStatusBadge({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: MerchBadgeTone;
}) {
  return (
    <Badge tone={tone} size="sm">
      {label}
    </Badge>
  );
}
