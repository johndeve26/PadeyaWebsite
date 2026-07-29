"use client";

import Link from "next/link";

import { BlogShare } from "@/components/blog/BlogShare";
import { BlogToc } from "@/components/blog/BlogToc";
import { Button } from "@/components/ui";
import type { BlogCategory, BlogPostListItem } from "@/lib/blog-api";
import { trackBlogCtaClick, trackBlogRelatedClick } from "@/lib/analytics";
import { brand } from "@/lib/brand";

type SidebarCta = { label: string; href: string; hint: string; ctaId: string };

function sidebarCtas(categorySlug?: string | null): SidebarCta[] {
  switch (categorySlug) {
    case "host-growth":
      return [
        { label: "Create event", href: "/host/events/new", hint: "Launch your next night", ctaId: "sidebar_create_event" },
        { label: "Host tools", href: "/for-hosts", hint: "Ticketing, check-in, Legacy", ctaId: "sidebar_host_tools" },
        { label: "Host workspace", href: "/host", hint: "Open your command center", ctaId: "sidebar_host_workspace" },
      ];
    case "safety":
      return [
        { label: "Safety Center", href: "/safety", hint: "Stay safe at the door", ctaId: "sidebar_safety" },
        { label: "Contact support", href: "/support", hint: "We’re here to help", ctaId: "sidebar_support" },
        { label: "Report an issue", href: "/report", hint: "Flag fraud or abuse", ctaId: "sidebar_report" },
      ];
    case "fans":
      return [
        { label: "For fans", href: "/fans", hint: "Passport, tickets, Connect", ctaId: "sidebar_fans" },
        { label: "Fan Passport", href: "/dashboard/passport", hint: "Your nightlife identity", ctaId: "sidebar_passport" },
        { label: "Explore events", href: "/events", hint: "Find your next night", ctaId: "sidebar_events" },
      ];
    case "product":
      return [
        { label: "Explore events", href: "/events", hint: "Browse what’s on", ctaId: "sidebar_events" },
        { label: "Shop merch", href: "/merch", hint: "Official drops", ctaId: "sidebar_merch" },
        { label: "Merch guide", href: "/merch-guide", hint: "How merch works", ctaId: "sidebar_merch_guide" },
      ];
    case "event-planning":
      return [
        { label: "Create event", href: "/host/events/new", hint: "Plan with Event Studio", ctaId: "sidebar_create_event" },
        { label: "Browse hosts", href: "/hosts", hint: "Learn from top hosts", ctaId: "sidebar_hosts" },
        { label: "Become a host", href: "/host/onboarding", hint: "Start hosting on Pàdéyá", ctaId: "sidebar_onboarding" },
      ];
    case "discovery":
    default:
      return [
        { label: "Explore events", href: "/events", hint: "Nights worth showing up for", ctaId: "sidebar_events" },
        { label: "Browse hosts", href: "/hosts", hint: "Follow hosts you trust", ctaId: "sidebar_hosts" },
        { label: "Shop merch", href: "/merch", hint: "Wear the night", ctaId: "sidebar_merch" },
      ];
  }
}

export function BlogArticleSidebar({
  html,
  title,
  path,
  category,
  related = [],
  postId,
  slug,
}: {
  html: string;
  title: string;
  path: string;
  category?: BlogCategory | null;
  related?: BlogPostListItem[];
  postId?: string;
  slug?: string;
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
            <BlogShare
              title={title}
              path={path}
              compact
              postId={postId}
              slug={slug}
            />
          </div>
        </div>

        {category ? (
          <div className="rounded-[var(--radius-lg)] border border-border bg-gradient-to-br from-surface-muted/80 to-card p-5 dark:from-surface-elevated dark:to-card">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Category
            </p>
            <Link
              href={`/blog/category/${category.slug}`}
              className="mt-2 block font-display text-lg font-bold text-heading hover:underline"
            >
              {category.name}
            </Link>
          </div>
        ) : null}

        <div className="rounded-[var(--radius-lg)] border border-border bg-ink p-5 text-paper">
          <p
            className="text-[11px] font-bold uppercase tracking-[0.18em]"
            style={{ color: brand.colors.green }}
          >
            On Pàdéyá
          </p>
          <ul className="mt-4 space-y-3">
            {ctas.map((cta) => (
              <li key={cta.href}>
                <Link
                  href={cta.href}
                  className="block"
                  onClick={() =>
                    trackBlogCtaClick({
                      postId,
                      ctaId: cta.ctaId,
                      ctaPath: cta.href,
                    })
                  }
                >
                  <Button size="sm" variant="outline-dark" className="w-full justify-start">
                    {cta.label}
                  </Button>
                  <span className="mt-1 block text-xs text-paper/60">{cta.hint}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {relatedLinks.length ? (
          <div className="rounded-[var(--radius-lg)] border border-border bg-card p-5">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Related
            </p>
            <ul className="mt-3 space-y-3">
              {relatedLinks.map((r) => (
                <li key={r.id}>
                  <Link
                    href={`/blog/${r.slug}`}
                    className="text-sm font-semibold text-heading hover:underline"
                    onClick={() => {
                      if (postId) {
                        trackBlogRelatedClick({
                          postId,
                          relatedPostId: r.id,
                          relatedSlug: r.slug,
                        });
                      }
                    }}
                  >
                    {r.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
