import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { HelpArticleCard } from "@/components/help/HelpArticleCard";
import { HelpSearch } from "@/components/help/HelpSearch";
import { HelpStillNeedHelp } from "@/components/help/HelpStillNeedHelp";
import { Container, EmptyState } from "@/components/ui";
import {
  fetchHelpArticlesServer,
  fetchHelpCategoryServer,
} from "@/lib/knowledge-base/api";
import { helpCategoryMetadata } from "@/lib/seo/help-metadata";

type Props = {
  params: Promise<{ categorySlug: string }>;
  searchParams: Promise<{ q?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug } = await params;
  const cat = await fetchHelpCategoryServer(categorySlug);
  if (!cat) return { title: "Category not found", robots: { index: false } };
  return helpCategoryMetadata(cat.name, cat.slug, cat.description);
}

export const revalidate = 300;

export default async function HelpCategoryPage({ params, searchParams }: Props) {
  const { categorySlug } = await params;
  const { q } = await searchParams;
  const query = (q || "").trim();
  const cat = await fetchHelpCategoryServer(categorySlug);
  if (!cat) notFound();

  const articles = await fetchHelpArticlesServer({
    category: cat.slug,
    q: query || undefined,
    limit: 50,
  });

  return (
    <main className="bg-background pb-20 pt-10 text-foreground sm:pt-14">
      <Container>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
          <Link href="/help" className="hover:text-primary-text">
            Help Center
          </Link>
          <span className="mx-2">/</span>
          <span className="text-heading">{cat.name}</span>
        </p>
        <header className="mt-4 max-w-2xl">
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-heading sm:text-4xl">
            {cat.name}
          </h1>
          {cat.description ? (
            <p className="mt-3 text-base text-muted-foreground sm:text-lg">
              {cat.description}
            </p>
          ) : null}
          <div className="mt-6 max-w-xl">
            <HelpSearch
              initialQuery={query}
              actionHref={`/help/${cat.slug}`}
            />
          </div>
        </header>

        {query ? (
          <p className="mt-8 text-sm text-muted-foreground">
            Showing matches for &ldquo;{query}&rdquo; in this category.
          </p>
        ) : null}

        {articles.length ? (
          <div className="mt-12 grid gap-8 sm:grid-cols-2">
            {articles.map((a) => (
              <HelpArticleCard key={a.id} article={a} />
            ))}
          </div>
        ) : (
          <div className="mt-12">
            <EmptyState
              title={
                query
                  ? "No answer found. Open a support ticket."
                  : "No published guides yet"
              }
              description={
                query
                  ? "Try another query or open Support with this topic."
                  : "Check back soon, or browse the full Help Center."
              }
              action={
                <Link
                  href={query ? "/support" : "/help"}
                  className="text-sm font-semibold text-primary-text"
                >
                  {query ? "Open support ticket" : "Back to Help"}
                </Link>
              }
            />
          </div>
        )}

        <div className="mt-16">
          <HelpStillNeedHelp />
        </div>
      </Container>
    </main>
  );
}
