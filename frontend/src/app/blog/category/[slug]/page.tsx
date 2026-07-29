import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { BlogCard } from "@/components/blog/BlogCard";
import { BlogIndexViewTracker } from "@/components/blog/BlogAnalyticsTrackers";
import { BlogFilterBar } from "@/components/blog/BlogFilterBar";
import { BlogRecoveryCtas } from "@/components/blog/BlogRecoveryCtas";
import { Container, EmptyState } from "@/components/ui";
import type { BlogCategory } from "@/lib/blog-api";
import {
  fetchBlogCategoriesServer,
  fetchBlogPostsServer,
  fetchBlogTaxonomyServer,
} from "@/lib/blog-api";
import { buildPageMetadata } from "@/lib/seo/site";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const cat = (await fetchBlogTaxonomyServer(
    "categories",
    slug,
  )) as BlogCategory | null;
  if (!cat) return { title: "Category", robots: { index: false } };
  return buildPageMetadata({
    title: `${cat.name} · Blog`,
    description: cat.description || `Posts in ${cat.name} on Pàdéyá.`,
    path: `/blog/category/${slug}`,
  });
}

export const revalidate = 300;

export default async function BlogCategoryPage({ params }: Props) {
  const { slug } = await params;
  const category = (await fetchBlogTaxonomyServer(
    "categories",
    slug,
  )) as BlogCategory | null;
  if (!category) notFound();
  const [posts, categories] = await Promise.all([
    fetchBlogPostsServer({ category: slug }),
    fetchBlogCategoriesServer(),
  ]);

  return (
    <main className="bg-background pb-20 pt-10">
      <BlogIndexViewTracker kind="category" slug={slug} />
      <Container>
        <h1 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          {category.name}
        </h1>
        {category.description ? (
          <p className="mt-3 max-w-xl text-muted-foreground">
            {category.description}
          </p>
        ) : null}
        <div className="mt-8">
          <BlogFilterBar categories={categories} activeSlug={slug} />
        </div>
        {posts.length ? (
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {posts.map((p) => (
              <BlogCard key={p.id} post={p} />
            ))}
          </div>
        ) : (
          <div className="mt-12">
            <EmptyState
              title="No posts in this category"
              description="Check back soon or browse all posts."
            />
          </div>
        )}
        <BlogRecoveryCtas />
      </Container>
    </main>
  );
}
