import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";

import { Badge } from "./Badge";
import { Card } from "./Card";

export function TicketCard({
  name,
  type,
  price,
  description,
  benefits,
  soldOut,
  selected,
  onSelect,
  className = "",
}: {
  name: string;
  type?: string;
  price: string | number;
  description?: string | null;
  benefits?: string | null;
  soldOut?: boolean;
  selected?: boolean;
  onSelect?: () => void;
  className?: string;
}) {
  const amount = Number(price);
  const label = Number.isFinite(amount)
    ? amount === 0
      ? "Free"
      : formatNgn(amount)
    : String(price);

  const interactive = Boolean(onSelect) && !soldOut;

  return (
    <Card
      hover={interactive}
      className={cn(
        "space-y-2",
        selected ? "border-accent shadow-[var(--shadow-glow)]" : "",
        soldOut ? "opacity-60" : "",
        interactive
          ? "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          : "",
        className,
      )}
      onClick={interactive ? onSelect : undefined}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-pressed={interactive ? Boolean(selected) : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect?.();
              }
            }
          : undefined
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-0.5">
          <p className="font-bold text-foreground">{name}</p>
          {type ? (
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              {type.replace(/_/g, " ")}
            </p>
          ) : null}
        </div>
        <p className="shrink-0 text-lg font-extrabold tracking-tight text-foreground">
          {label}
        </p>
      </div>
      {description ? (
        <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
      ) : null}
      {benefits ? (
        <p className="text-sm leading-relaxed text-muted-foreground">{benefits}</p>
      ) : null}
      {soldOut ? <Badge tone="danger">Sold out</Badge> : null}
      {selected && !soldOut ? <Badge tone="accent">Selected</Badge> : null}
    </Card>
  );
}
