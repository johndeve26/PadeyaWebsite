import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";

const LABELS: Record<string, string> = {
  listed: "Listed",
  unlisted: "Unlisted",
  password_protected: "Password",
  approval_required: "Approval required",
  public: "Public",
  private: "Private",
  invite_only: "Invite only",
  secret_location: "Secret location",
  online: "Online",
  hybrid: "Hybrid",
  full_public: "Full address",
  area_only: "Area only",
  hidden_until_payment: "Hidden until payment",
  hidden_until_24h_before: "Reveal 24h before",
  hidden_until_manual_approval: "Manual reveal",
  online_only: "Online only",
};

export function EventVisibilityBadge({
  value,
  tone = "neutral",
  className,
}: {
  value?: string | null;
  tone?: "neutral" | "accent" | "success" | "warning";
  className?: string;
}) {
  if (!value) return null;
  return (
    <Badge
      tone={tone}
      className={cn("max-w-full truncate capitalize", className)}
    >
      {LABELS[value] ?? value.replaceAll("_", " ")}
    </Badge>
  );
}
