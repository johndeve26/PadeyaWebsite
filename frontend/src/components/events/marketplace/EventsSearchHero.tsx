import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";

export function EventsSearchHero({
  title = "Find events on Pàdéyá",
  description = "Search upcoming events by city, category, date, budget, and access.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <section
      {...headerDarkSurfaceProps}
      className="border-b border-border bg-ink text-paper"
    >
      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">
          Events
        </p>
        <h1 className="mt-2 max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl">
          {title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-subtle-foreground sm:text-base">
          {description}
        </p>
        <p className="mt-4 text-xs font-semibold text-subtle-foreground sm:text-sm">
          Verified hosts · Secure tickets · QR entry
        </p>
      </div>
    </section>
  );
}
