import { cn } from "@/lib/cn";

/** Compact calendar badge — month + day + weekday, as on classic event listings. */
export function EventDateBadge({
  date,
  className = "",
}: {
  date: string | Date;
  className?: string;
}) {
  const d = typeof date === "string" ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return null;

  const month = d.toLocaleDateString("en-NG", { month: "short" }).toUpperCase();
  const day = d.getDate().toString().padStart(2, "0");
  const weekday = d.toLocaleDateString("en-NG", { weekday: "long" });

  return (
    <div
      className={cn(
        "flex w-[4.75rem] shrink-0 flex-col overflow-hidden rounded-[var(--radius-md)] border border-border bg-card text-center shadow-[var(--shadow-soft)]",
        className,
      )}
      aria-hidden
    >
      <div className="bg-accent px-1 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.14em] text-primary-foreground">
        {month}
      </div>
      <div className="px-1 py-2">
        <p className="text-2xl font-extrabold leading-none tracking-tight text-foreground">
          {day}
        </p>
        <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
          {weekday}
        </p>
      </div>
    </div>
  );
}
