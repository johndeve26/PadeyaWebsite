import type { Metadata } from "next";
import Link from "next/link";

import { BlogCard } from "@/components/blog/BlogCard";
import { BlogIndexViewTracker } from "@/components/blog/BlogAnalyticsTrackers";
import { BlogFilterBar } from "@/components/blog/BlogFilterBar";
import { BlogRecoveryCtas } from "@/components/blog/BlogRecoveryCtas";
import { Container, EmptyState } from "@/components/ui";
import {
  fetchBlogCategoriesServer,
  fetchBlogPostsServer,
} from "@/lib/blog-api";
import { brand } from "@/lib/brand";
import { blogIndexMetadata } from "@/lib/seo/blog-metadata";

export const metadata: Metadata = blogIndexMetadata();

export const revalidate = 300;

export default async function BlogIndexPage() {
  const [posts, categories] = await Promise.all([
    fetchBlogPostsServer({ limit: 50 }),
    fetchBlogCategoriesServer(),
  ]);

  const featured = posts.find((p) => p.is_featured) || posts[0];
  const rest = posts.filter((p) => p.id !== featured?.id);

  return (
    <main className="bg-background pb-20 pt-10 text-foreground">
      <BlogIndexViewTracker />
      <Container>
        <header className="max-w-2xl">
          <p
            className="text-xs font-bold uppercase tracking-[0.16em]"
            style={{ color: brand.colors.green }}
          >
            {brand.name} Blog
          </p>
          <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-heading sm:text-5xl">
            Stories for the night
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
            Editorial for fans and hosts — event discovery, ticketing safety,
            host growth, Fan Passport, Ambassadors, sponsorships, and platform
            updates on Pàdéyá.
          </p>
        </header>

        <div className="mt-8">
          <BlogFilterBar categories={categories} />
        </div>

        {!posts.length ? (
          <div className="mt-12">
            <EmptyState
              title="No blog posts published yet"
              description="New editorial is on the way. Explore events or open Support if you need help now."
              action={
                <Link href="/events" className="text-sm font-semibold text-primary">
                  Explore events
                </Link>
              }
            />
          </div>
        ) : null}

        {featured ? (
          <div className="mt-10">
            <BlogCard post={featured} featured />
          </div>
        ) : null}

        {rest.length ? (
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {rest.map((post) => (
              <BlogCard key={post.id} post={post} />
            ))}
          </div>
        ) : null}

        <BlogRecoveryCtas />
      </Container>
    </main>
  );
}
