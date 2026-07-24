import Link from "next/link";

import { cn } from "@/lib/cn";

import { Badge } from "./Badge";
import { Card } from "./Card";
import { Media } from "./Media";

export function SponsorCard({
  name,
  description,
  href,
  imageUrl,
  category,
  className = "",
}: {
  name: string;
  description?: string | null;
  href?: string;
  imageUrl?: string | null;
  category?: string | null;
  className?: string;
}) {
  const body = (
    <Card hover className={cn("h-full space-y-3", className)}>
      <div className="relative h-14 w-full overflow-hidden rounded-[var(--radius-sm)] bg-muted">
        {imageUrl ? (
          <Media src={imageUrl} className="object-contain p-2" />
        ) : (
          <div className="flex h-full items-center justify-center text-sm font-bold text-muted-foreground">
            {name}
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-bold text-foreground">{name}</h3>
        {category ? <Badge tone="neutral">{category}</Badge> : null}
      </div>
      {description ? (
        <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
      ) : null}
    </Card>
  );

  if (!href) return body;
  return (
    <Link href={href} className="block h-full">
      {body}
    </Link>
  );
}
