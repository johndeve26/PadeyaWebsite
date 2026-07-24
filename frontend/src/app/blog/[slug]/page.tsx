import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  BlogArticleBody,
  blogArticleHtmlWithIds,
} from "@/components/blog/BlogArticleBody";
import { BlogArticleSidebar } from "@/components/blog/BlogArticleSidebar";
import { BlogCard } from "@/components/blog/BlogCard";
import { BlogComments } from "@/components/blog/BlogComments";
import { BlogRecoveryCtas } from "@/components/blog/BlogRecoveryCtas";
import { BlogShare } from "@/components/blog/BlogShare";
import { Container } from "@/components/ui";
import { fetchBlogPostServer } from "@/lib/blog-api";
import {
  blogCategoryGradient,
  blogCoverAlt,
  resolveBlogCoverUrl,
} from "@/lib/blog-cover";
import { brand } from "@/lib/brand";
import {
  articleJsonLd,
  blogPostMetadata,
} from "@/lib/seo/blog-metadata";
import { JsonLdScript } from "@/lib/seo/jsonld";
import { siteOrigin } from "@/lib/seo/site";

type Props = { params: Promise<{ slug: string }> };

function formatLongDate(iso?: string | null) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = await fetchBlogPostServer(slug);
  if (!post) {
    return { title: "Post not found", robots: { index: false, follow: false } };
  }
  return blogPostMetadata(post);
}

export const revalidate = 300;

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params;
  const post = await fetchBlogPostServer(slug);
  if (!post || post.status !== "published") notFound();

  const origin = siteOrigin();
  const published = formatLongDate(post.published_at);
  const updated = formatLongDate(post.updated_at);
  const showUpdated =
    Boolean(post.updated_at && post.published_at) &&
    post.updated_at !== post.published_at &&
    updated &&
    updated !== published;

  const authorName = post.author?.display_name || `${brand.name} Editorial`;
  const authorInitial = authorName.trim().slice(0, 1).toUpperCase() || "P";
  const { src: coverSrc, isPlaceholder } = resolveBlogCoverUrl(
    post.cover_url,
    post.category,
  );
  const coverAlt = blogCoverAlt(post.title, post.category);
  const bodyHtml = blogArticleHtmlWithIds(post.body_html);
  const related = (post.related ?? []).slice(0, 3);

  return (
    <main className="relative overflow-hidden bg-background pb-20 pt-8 text-foreground sm:pt-12">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[28rem] bg-[radial-gradient(ellipse_80%_55%_at_50%_-10%,color-mix(in_srgb,var(--primary)_14%,transparent),transparent_60%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent"
      />

      <JsonLdScript data={articleJsonLd(post, origin)} />

      <Container className="relative space-y-10 sm:space-y-12">
        <header className="max-w-4xl space-y-5">
          <p className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.2em] text-heading">
            <span
              aria-hidden
              className="inline-block h-[3px] w-7 shrink-0 rounded-[1px] bg-primary"
            />
            <span>
              <Link
                href="/blog"
                className="transition-colors hover:text-primary-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
              >
                Blog
              </Link>
              {post.category ? (
                <>
                  <span className="text-muted-foreground"> / </span>
                  <Link
                    href={`/blog/category/${post.category.slug}`}
                    className="transition-colors hover:text-primary-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                  >
                    {post.category.name}
                  </Link>
                </>
              ) : null}
            </span>
          </p>

          <h1 className="text-balance font-display text-3xl font-extrabold tracking-tight text-heading sm:text-5xl sm:leading-[1.08] md:text-[3.25rem]">
            {post.title}
          </h1>

          {post.excerpt ? (
            <p className="max-w-3xl text-pretty text-lg leading-relaxed text-foreground/75 sm:text-xl sm:leading-relaxed">
              {post.excerpt}
            </p>
          ) : null}

          <div className="flex flex-col gap-5 border-y border-border/80 bg-card/40 py-4 backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between dark:bg-surface-elevated/40">
            <div className="flex min-w-0 items-center gap-3">
              {post.author?.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={post.author.avatar_url}
                  alt=""
                  className="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
                />
              ) : (
                <div
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-primary"
                  aria-hidden
                >
                  {authorInitial}
                </div>
              )}
              <div className="min-w-0 space-y-0.5">
                {post.author ? (
                  <Link
                    href={`/blog/author/${post.author.slug}`}
                    className="block truncate font-semibold text-heading transition-colors hover:text-primary-text"
                  >
                    {authorName}
                  </Link>
                ) : (
                  <p className="truncate font-semibold text-heading">
                    {authorName}
                  </p>
                )}
                <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground sm:text-sm">
                  {published ? (
                    <time dateTime={post.published_at ?? undefined}>
                      {published}
                    </time>
                  ) : null}
                  {showUpdated ? (
                    <>
                      <span aria-hidden>·</span>
                      <span>
                        Updated{" "}
                        <time dateTime={post.updated_at ?? undefined}>
                          {updated}
                        </time>
                      </span>
                    </>
                  ) : null}
                  <span aria-hidden>·</span>
                  <span>{post.reading_time_minutes} min read</span>
                </p>
              </div>
            </div>
            <BlogShare title={post.title} path={`/blog/${post.slug}`} />
          </div>
        </header>

        {coverSrc ? (
          <figure className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink shadow-[var(--shadow)]">
            <div
              className="relative aspect-[21/9] sm:aspect-[2.4/1]"
              style={
                isPlaceholder
                  ? { background: blogCategoryGradient(post.category) }
                  : undefined
              }
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={coverSrc}
                alt={coverAlt}
                className={
                  isPlaceholder
                    ? "h-full w-full object-cover opacity-95"
                    : "h-full w-full object-cover"
                }
              />
            </div>
            <figcaption className="sr-only">{coverAlt}</figcaption>
          </figure>
        ) : (
          <div
            aria-hidden
            className="h-2 w-full rounded-full bg-gradient-to-r from-primary via-primary/40 to-transparent"
          />
        )}

        <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_280px] lg:gap-12 xl:gap-16">
          <div className="min-w-0 space-y-10">
            <BlogArticleBody html={post.body_html} />

            <div className="flex flex-col gap-5 border-t border-border pt-8 sm:flex-row sm:items-center sm:justify-between">
              <BlogShare title={post.title} path={`/blog/${post.slug}`} />
              {post.tags?.length ? (
                <div className="flex flex-wrap gap-2" aria-label="Tags">
                  {post.tags.map((t) => (
                    <Link
                      key={t.id}
                      href={`/blog/tag/${t.slug}`}
                      className="rounded-full border border-border bg-card px-3.5 py-1.5 text-xs font-semibold text-heading transition-colors hover:border-primary/50 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                    >
                      #{t.name}
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>

            <BlogComments postSlug={post.slug} />
          </div>

          <div className="hidden lg:block">
            <BlogArticleSidebar
              html={bodyHtml}
              title={post.title}
              path={`/blog/${post.slug}`}
              category={post.category}
              related={post.related}
            />
          </div>
        </div>

        {/* Mobile: compact related guides + CTAs (sidebar is desktop-only) */}
        <div className="space-y-4 lg:hidden">
          {post.category ? (
            <Link
              href={`/blog/category/${post.category.slug}`}
              className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-border bg-card px-4 py-3 text-sm font-semibold text-heading"
            >
              More in {post.category.name} →
            </Link>
          ) : null}
        </div>

        {related.length ? (
          <section className="space-y-6 border-t border-border pt-12">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.2em] text-heading">
                  <span
                    aria-hidden
                    className="inline-block h-[3px] w-7 shrink-0 rounded-[1px] bg-primary"
                  />
                  Keep reading
                </p>
                <h2 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-heading sm:text-3xl">
                  Related posts
                </h2>
              </div>
              <Link
                href="/blog"
                className="text-sm font-semibold text-primary-text hover:underline"
              >
                All posts →
              </Link>
            </div>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {related.map((r) => (
                <BlogCard key={r.id} post={r} />
              ))}
            </div>
          </section>
        ) : null}

        <BlogRecoveryCtas categorySlug={post.category?.slug} />
      </Container>
    </main>
  );
}
