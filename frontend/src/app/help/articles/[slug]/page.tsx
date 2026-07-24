import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { BlogArticleBody } from "@/components/blog/BlogArticleBody";
import { HelpArticleCard } from "@/components/help/HelpArticleCard";
import { HelpFeedback } from "@/components/help/HelpFeedback";
import { HelpStillNeedHelp } from "@/components/help/HelpStillNeedHelp";
import { HelpVideoEmbed } from "@/components/help/HelpVideoEmbed";
import { Container } from "@/components/ui";
import { fetchHelpArticleServer } from "@/lib/knowledge-base/api";
import { brand } from "@/lib/brand";
import {
  helpArticleJsonLd,
  helpArticleMetadata,
} from "@/lib/seo/help-metadata";
import { JsonLdScript } from "@/lib/seo/jsonld";
import { siteOrigin } from "@/lib/seo/site";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const article = await fetchHelpArticleServer(slug);
  if (!article) {
    return { title: "Article not found", robots: { index: false, follow: false } };
  }
  return helpArticleMetadata(article);
}

export const revalidate = 300;

export default async function HelpArticlePage({ params }: Props) {
  const { slug } = await params;
  const article = await fetchHelpArticleServer(slug);
  if (!article || article.status !== "published") notFound();

  const origin = siteOrigin();
  const updated = article.updated_at
    ? new Date(article.updated_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <main className="bg-background pb-20 pt-8 text-foreground sm:pt-12">
      <JsonLdScript data={helpArticleJsonLd(article, origin)} />

      <Container className="space-y-10 sm:space-y-12">
        <header className="max-w-4xl space-y-5">
          <p className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.2em] text-heading">
            <span
              aria-hidden
              className="inline-block h-[3px] w-7 shrink-0 rounded-[1px] bg-primary"
            />
            <span>
              <Link
                href="/help"
                className="transition-colors hover:text-primary-text"
              >
                Help
              </Link>
              {article.category ? (
                <>
                  <span className="text-muted-foreground"> / </span>
                  <Link
                    href={`/help/${article.category.slug}`}
                    className="transition-colors hover:text-primary-text"
                  >
                    {article.category.name}
                  </Link>
                </>
              ) : null}
            </span>
          </p>

          <h1 className="text-balance font-display text-3xl font-extrabold tracking-tight text-heading sm:text-5xl sm:leading-[1.08]">
            {article.title}
          </h1>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-foreground/70">
            <span className="font-semibold text-heading">{brand.name} Help</span>
            {updated ? (
              <>
                <span aria-hidden>·</span>
                <span>Updated {updated}</span>
              </>
            ) : null}
            <span aria-hidden>·</span>
            <span>{article.reading_time_minutes} min read</span>
            {article.audiences?.length ? (
              <>
                <span aria-hidden>·</span>
                <span className="capitalize">
                  For {article.audiences.join(", ")}
                </span>
              </>
            ) : null}
            {article.difficulty ? (
              <>
                <span aria-hidden>·</span>
                <span className="capitalize">{article.difficulty}</span>
              </>
            ) : null}
          </div>

          {article.excerpt ? (
            <p className="max-w-3xl text-pretty text-lg leading-relaxed text-foreground/75 sm:text-xl">
              {article.excerpt}
            </p>
          ) : null}
        </header>

        <HelpVideoEmbed
          embedUrl={article.video_embed_url}
          title={article.title}
          provider={article.video_provider}
          externalUrl={article.video_url}
        />

        <BlogArticleBody html={article.body_html} />

        <section className="max-w-3xl border-t border-border pt-8">
          <HelpFeedback articleId={article.id} />
        </section>

        {article.related && article.related.length > 0 ? (
          <section>
            <h2 className="font-display text-xl font-extrabold tracking-tight text-heading">
              Related guides
            </h2>
            <div className="mt-6 grid gap-8 sm:grid-cols-2">
              {article.related.map((a) => (
                <HelpArticleCard key={a.id} article={a} />
              ))}
            </div>
          </section>
        ) : null}

        <HelpStillNeedHelp />
      </Container>
    </main>
  );
}
