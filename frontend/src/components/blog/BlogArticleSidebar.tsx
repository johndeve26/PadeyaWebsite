import Link from "next/link";

import { BlogShare } from "@/components/blog/BlogShare";
import { BlogToc } from "@/components/blog/BlogToc";
import { Button } from "@/components/ui";
import type { BlogCategory, BlogPostListItem } from "@/lib/blog-api";
import { brand } from "@/lib/brand";

type SidebarCta = { label: string; href: string; hint: string };

function sidebarCtas(categorySlug?: string | null): SidebarCta[] {
  switch (categorySlug) {
    case "host-growth":
      return [
        { label: "Create event", href: "/host/events/new", hint: "Launch your next night" },
        { label: "Host tools", href: "/for-hosts", hint: "Ticketing, check-in, Legacy" },
        { label: "Host workspace", href: "/host", hint: "Open your command center" },
      ];
    case "safety":
      return [
        { label: "Safety Center", href: "/safety", hint: "Stay safe at the door" },
        { label: "Contact support", href: "/support", hint: "We’re here to help" },
        { label: "Report an issue", href: "/report", hint: "Flag fraud or abuse" },
      ];
    case "fans":
      return [
        { label: "For fans", href: "/fans", hint: "Passport, tickets, Connect" },
        { label: "Fan Passport", href: "/dashboard/passport", hint: "Your nightlife identity" },
        { label: "Explore events", href: "/events", hint: "Find your next night" },
      ];
    case "product":
      return [
        { label: "Explore events", href: "/events", hint: "Browse what’s on" },
        { label: "Shop merch", href: "/merch", hint: "Official drops" },
        { label: "Merch guide", href: "/merch-guide", hint: "How merch works" },
      ];
    case "event-planning":
      return [
        { label: "Create event", href: "/host/events/new", hint: "Plan with Event Studio" },
        { label: "Browse hosts", href: "/hosts", hint: "Learn from top hosts" },
        { label: "Become a host", href: "/host/onboarding", hint: "Start hosting on Pàdéyá" },
      ];
    case "discovery":
    default:
      return [
        { label: "Explore events", href: "/events", hint: "Nights worth showing up for" },
        { label: "Browse hosts", href: "/hosts", hint: "Follow hosts you trust" },
        { label: "Shop merch", href: "/merch", hint: "Wear the night" },
      ];
  }
}

export function BlogArticleSidebar({
  html,
  title,
  path,
  category,
  related = [],
}: {
  html: string;
  title: string;
  path: string;
  category?: BlogCategory | null;
  related?: BlogPostListItem[];
}) {
  const ctas = sidebarCtas(category?.slug);
  const relatedLinks = related.slice(0, 4);

  return (
    <aside className="space-y-5" aria-label="Article sidebar">
      <div className="sticky top-24 space-y-5">
        <BlogToc html={html} />

        <div className="rounded-[var(--radius-lg)] border border-border bg-card/80 p-5 shadow-[var(--shadow-soft)] backdrop-blur-sm dark:bg-surface-elevated">
          <p className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-heading">
            <span
              aria-hidden
              className="inline-block h-[3px] w-5 shrink-0 rounded-[1px] bg-primary"
            />
            Share
          </p>
          <div className="mt-4">
            <BlogShare title={title} path={path} compact />
          </div>
        </div>

        {category ? (
          <div className="rounded-[var(--radius-lg)] border border-border bg-gradient-to-br from-surface-muted/80 to-card p-5 dark:from-surface-elevated dark:to-card">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Category
            </p>
            <Link
              href={`/blog/category/${category.slug}`}
              className="mt-2 inline-flex font-display text-lg font-extrabold tracking-tight text-heading transition-colors hover:text-primary-text"
            >
              {category.name}
            </Link>
            {category.description ? (
              <p className="mt-2 text-sm leading-relaxed text-foreground/70">
                {category.description}
              </p>
            ) : (
              <p className="mt-2 text-sm leading-relaxed text-foreground/70">
                More guides in this series on {brand.name}.
              </p>
            )}
            <Link
              href={`/blog/category/${category.slug}`}
              className="mt-3 inline-flex text-sm font-semibold text-primary-text hover:underline"
            >
              View category →
            </Link>
          </div>
        ) : null}

        {relatedLinks.length ? (
          <div className="rounded-[var(--radius-lg)] border border-border bg-card p-5 shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
            <p className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-heading">
              <span
                aria-hidden
                className="inline-block h-[3px] w-5 shrink-0 rounded-[1px] bg-primary"
              />
              Related guides
            </p>
            <ul className="mt-4 space-y-3 border-t border-border pt-4">
              {relatedLinks.map((r) => (
                <li key={r.id}>
                  <Link
                    href={`/blog/${r.slug}`}
                    className="group block"
                  >
                    {r.category ? (
                      <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary-text">
                        {r.category.name}
                      </span>
                    ) : null}
                    <span className="mt-0.5 block text-sm font-semibold leading-snug text-heading transition-colors group-hover:text-primary-text">
                      {r.title}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="relative overflow-hidden rounded-[var(--radius-lg)] border border-border bg-ink p-5 text-paper shadow-[var(--shadow)]">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,color-mix(in_srgb,var(--primary)_18%,transparent),transparent_55%)]"
          />
          <p
            className="relative text-[11px] font-bold uppercase tracking-[0.18em]"
            style={{ color: brand.colors.green }}
          >
            On {brand.name}
          </p>
          <ul className="relative mt-4 space-y-4">
            {ctas.map((cta) => (
              <li key={cta.href} className="space-y-1.5">
                <p className="text-sm font-semibold tracking-tight">{cta.label}</p>
                <p className="text-xs leading-relaxed text-paper/65">{cta.hint}</p>
                <Link href={cta.href}>
                  <Button size="sm" variant="outline-dark" className="mt-1">
                    {cta.label}
                  </Button>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}
