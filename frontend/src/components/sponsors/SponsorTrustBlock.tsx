import { cn } from "@/lib/cn";

const DEFAULT_ITEMS = [
  {
    title: "Verified Legacy Pages",
    body: "Public host profiles with reputation that compounds after every night.",
  },
  {
    title: "Checked-in audience history",
    body: "Attendance signals from real QR check-ins — not vanity claims.",
  },
  {
    title: "Sponsor-branded integrations",
    body: "Event pages, ticket emails, Legacy, Vault, and Memory placements.",
  },
  {
    title: "Admin-moderated listings",
    body: "Slots can be flagged, approved, or removed with audit trails.",
  },
  {
    title: "Event-native placements",
    body: "Sponsorships sit inside real nights — not generic ad inventory.",
  },
  {
    title: "Clear inquiry workflow",
    body: "Brands inquire in-product. Hosts review — nothing auto-approves.",
  },
];

export function SponsorTrustBlock({
  title = "Why brands trust Pàdéyá",
  description = "Proof, moderation, and a commercial path brands can diligence.",
  items = DEFAULT_ITEMS,
  className = "",
}: {
  title?: string;
  description?: string;
  items?: { title: string; body: string }[];
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-[var(--radius-xl)] border border-border bg-muted/70 px-5 py-7 sm:px-8 sm:py-8",
        className,
      )}
    >
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
        Trust
      </p>
      <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
        {title}
      </h2>
      {description ? (
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:text-base">
          {description}
        </p>
      ) : null}
      <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <div key={item.title} className="space-y-2">
            <div className="h-1 w-7 rounded-full bg-accent" />
            <h3 className="font-bold text-foreground">{item.title}</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {item.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
