import type { Metadata } from "next";
import Link from "next/link";

import { HelpArticleCard } from "@/components/help/HelpArticleCard";
import { HelpCategoryGrid } from "@/components/help/HelpCategoryGrid";
import { HelpQuickCards } from "@/components/help/HelpQuickCards";
import { HelpRoleCards } from "@/components/help/HelpRoleCards";
import { HelpSearch } from "@/components/help/HelpSearch";
import { HelpStillNeedHelp } from "@/components/help/HelpStillNeedHelp";
import { Button, Container, EmptyState } from "@/components/ui";
import {
  fetchHelpArticlesServer,
  fetchHelpCategoriesServer,
  HELP_GROUP_LABELS,
} from "@/lib/knowledge-base/api";
import { brand } from "@/lib/brand";
import { helpIndexMetadata } from "@/lib/seo/help-metadata";

export const metadata: Metadata = helpIndexMetadata();
export const revalidate = 300;

type Props = { searchParams: Promise<{ q?: string; audience?: string }> };

function groupSearchHits(
  hits: Awaited<ReturnType<typeof fetchHelpArticlesServer>>,
) {
  const map = new Map<string, typeof hits>();
  for (const article of hits) {
    const key = article.category?.group_key || article.category?.name || "general";
    const list = map.get(key) || [];
    list.push(article);
    map.set(key, list);
  }
  return map;
}

export default async function HelpCenterPage({ searchParams }: Props) {
  const { q, audience: audienceParam } = await searchParams;
  const query = (q || "").trim();
  const audience = (audienceParam || "").trim() || undefined;

  const [categories, featured, popular, searchHits, fan, host, audienceHits] =
    await Promise.all([
      fetchHelpCategoriesServer(),
      fetchHelpArticlesServer({ featured: true, limit: 4 }),
      fetchHelpArticlesServer({ popular: true, limit: 8 }),
      query
        ? fetchHelpArticlesServer({ q: query, limit: 30 })
        : Promise.resolve([]),
      fetchHelpArticlesServer({ audience: "fan", limit: 4 }),
      fetchHelpArticlesServer({ audience: "host", limit: 4 }),
      audience && !query
        ? fetchHelpArticlesServer({ audience, limit: 20 })
        : Promise.resolve([]),
    ]);

  const groupedHits = query ? groupSearchHits(searchHits) : null;

  return (
    <main className="relative overflow-hidden bg-background pb-20 pt-10 text-foreground sm:pt-14">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_color-mix(in_srgb,var(--primary)_14%,transparent),_transparent_55%),linear-gradient(180deg,var(--surface-muted),var(--background))]"
      />

      <Container>
        <header className="mx-auto max-w-3xl text-center">
          <p
            className="text-xs font-bold uppercase tracking-[0.16em]"
            style={{ color: brand.colors.green }}
          >
            {brand.name} Help Center
          </p>
          <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-heading sm:text-5xl">
            How can we help?
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Guides for fans, hosts, sponsors, ambassadors, and visitors —
            tickets, hosting, Fan Passport, safety, and more.
          </p>
          <div className="mx-auto mt-8 max-w-2xl text-left">
            <HelpSearch initialQuery={query} />
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
            <Link href="/support">
              <Button variant="secondary">Contact support</Button>
            </Link>
            <Link href="/faq">
              <Button variant="ghost">Browse FAQs</Button>
            </Link>
            <Link href="/merch-guide">
              <Button variant="ghost">Merch overview</Button>
            </Link>
          </div>
        </header>

        {query ? (
          <section className="mt-14">
            <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading">
              Results for &ldquo;{query}&rdquo;
            </h2>
            {searchHits.length && groupedHits ? (
              <div className="mt-8 space-y-12">
                {[...groupedHits.entries()].map(([group, articles]) => (
                  <div key={group}>
                    <h3 className="font-display text-lg font-extrabold text-heading">
                      {HELP_GROUP_LABELS[group] || group}
                    </h3>
                    <div className="mt-5 grid gap-8 sm:grid-cols-2">
                      {articles.map((a) => (
                        <HelpArticleCard key={a.id} article={a} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-8">
                <EmptyState
                  title="No answer found. Open a support ticket."
                  description="Try a shorter query, browse categories below, or open Support with your topic."
                  action={
                    <Link href="/support" className="text-sm font-semibold text-primary-text">
                      Open support ticket
                    </Link>
                  }
                />
              </div>
            )}
          </section>
        ) : null}

        {!query && audience && audienceHits.length ? (
          <section className="mt-14">
            <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading capitalize">
              {HELP_GROUP_LABELS[audience] || `${audience} guides`}
            </h2>
            <div className="mt-8 grid gap-8 sm:grid-cols-2">
              {audienceHits.map((a) => (
                <HelpArticleCard key={a.id} article={a} />
              ))}
            </div>
          </section>
        ) : null}

        {!query && !audience ? (
          <>
            <section className="mt-16">
              <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading">
                Quick help
              </h2>
              <div className="mt-6">
                <HelpQuickCards />
              </div>
            </section>

            {featured.length ? (
              <section className="mt-16">
                <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading">
                  Featured
                </h2>
                <div className="mt-8 grid gap-8 sm:grid-cols-2">
                  {featured.map((a) => (
                    <HelpArticleCard key={a.id} article={a} featured />
                  ))}
                </div>
              </section>
            ) : null}

            <section className="mt-16">
              <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading">
                Browse by topic
              </h2>
              <div className="mt-8">
                <HelpCategoryGrid categories={categories} />
              </div>
            </section>

            {popular.length ? (
              <section className="mt-16">
                <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading">
                  Popular articles
                </h2>
                <div className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
                  {popular.map((a) => (
                    <HelpArticleCard key={a.id} article={a} />
                  ))}
                </div>
              </section>
            ) : null}

            <section className="mt-16">
              <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading">
                Help by role
              </h2>
              <div className="mt-6">
                <HelpRoleCards />
              </div>
            </section>

            <section className="mt-16 grid gap-12 lg:grid-cols-2">
              <div>
                <h2 className="font-display text-xl font-extrabold tracking-tight text-heading">
                  {HELP_GROUP_LABELS.fan}
                </h2>
                <div className="mt-6 space-y-6">
                  {fan.map((a) => (
                    <HelpArticleCard key={a.id} article={a} />
                  ))}
                </div>
              </div>
              <div>
                <h2 className="font-display text-xl font-extrabold tracking-tight text-heading">
                  {HELP_GROUP_LABELS.host}
                </h2>
                <div className="mt-6 space-y-6">
                  {host.map((a) => (
                    <HelpArticleCard key={a.id} article={a} />
                  ))}
                </div>
              </div>
            </section>
          </>
        ) : null}

        <div className="mt-16">
          <HelpStillNeedHelp />
        </div>
      </Container>
    </main>
  );
}
