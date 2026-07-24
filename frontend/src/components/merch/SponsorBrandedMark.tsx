import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";

type Props = {
  brandName?: string | null;
  logoUrl?: string | null;
  description?: string | null;
  /** Compact badge + partnership line for cards */
  compact?: boolean;
  className?: string;
};

/** Public sponsor-branded merch mark — brand name/logo only, no private contact. */
export function SponsorBrandedMark({
  brandName,
  logoUrl,
  description,
  compact = false,
  className,
}: Props) {
  if (!brandName && !logoUrl) {
    return (
      <Badge tone="accent" size="sm" className={className}>
        Sponsor-branded
      </Badge>
    );
  }

  if (compact) {
    return (
      <div className={cn("space-y-1", className)}>
        <Badge tone="accent" size="sm">
          Sponsor-branded
        </Badge>
        {brandName ? (
          <p className="text-xs text-muted-foreground">
            In partnership with {brandName}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="accent" size="sm">
          Sponsor-branded
        </Badge>
        {logoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={logoUrl}
            alt={brandName ? `${brandName} logo` : "Sponsor logo"}
            className="h-7 w-auto max-w-[120px] object-contain"
          />
        ) : null}
      </div>
      {brandName ? (
        <p className="text-sm text-muted-foreground">
          In partnership with{" "}
          <span className="font-semibold text-foreground">{brandName}</span>
        </p>
      ) : null}
      {description ? (
        <p className="text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      ) : null}
    </div>
  );
}
