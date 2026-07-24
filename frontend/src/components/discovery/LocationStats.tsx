import { Container } from "@/components/ui";
import { cn } from "@/lib/cn";

export type LocationStatItem = {
  label: string;
  value: string | number;
};

/**
 * Compact location hub stats strip (upcoming events, hosts, categories…).
 */
export function LocationStats({
  name,
  stats,
  className = "",
}: {
  name: string;
  stats: LocationStatItem[];
  className?: string;
}) {
  if (!stats.length) return null;

  return (
    <section
      aria-label={`${name} stats`}
      className={cn(
        "border-b border-border bg-card py-8 sm:py-10",
        className,
      )}
    >
      <Container
        className={cn(
          "grid gap-4",
          stats.length >= 4
            ? "sm:grid-cols-2 lg:grid-cols-4"
            : "sm:grid-cols-2 lg:grid-cols-3",
        )}
      >
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-[var(--radius-lg)] border border-border bg-muted/50 px-4 py-5"
          >
            <p className="text-3xl font-extrabold tracking-tight text-foreground">
              {stat.value}
            </p>
            <p className="mt-1 text-sm font-semibold text-muted-foreground">
              {stat.label}
            </p>
          </div>
        ))}
      </Container>
    </section>
  );
}
