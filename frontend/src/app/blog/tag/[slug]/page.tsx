import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";

import { BlogCard } from "@/components/blog/BlogCard";
import { BlogIndexViewTracker } from "@/components/blog/BlogAnalyticsTrackers";
import { BlogRecoveryCtas } from "@/components/blog/BlogRecoveryCtas";
import { Container, EmptyState } from "@/components/ui";
import type { BlogTag } from "@/lib/blog-api";
import {
  fetchBlogPostsServer,
  fetchBlogTaxonomyServer,
} from "@/lib/blog-api";
import { buildPageMetadata } from "@/lib/seo/site";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const tag = (await fetchBlogTaxonomyServer("tags", slug)) as BlogTag | null;
  if (!tag) return { title: "Tag", robots: { index: false } };
  const canonical = tag.slug || slug;
  return buildPageMetadata({
    title: `#${tag.name} · Blog`,
    description: tag.description || `Posts tagged ${tag.name} on Pàdéyá.`,
    path: `/blog/tag/${canonical}`,
  });
}

export const revalidate = 300;

export default async function BlogTagPage({ params }: Props) {
  const { slug } = await params;
  const tag = (await fetchBlogTaxonomyServer("tags", slug)) as BlogTag | null;
  if (!tag) notFound();
  if (tag.slug && tag.slug !== slug) {
    permanentRedirect(`/blog/tag/${tag.slug}`);
  }
  const posts = await fetchBlogPostsServer({ tag: tag.slug || slug });

  return (
    <main className="bg-background pb-20 pt-10">
      <BlogIndexViewTracker kind="tag" slug={slug} />
      <Container>
        <h1 className="font-display text-3xl font-extrabold tracking-tight">
          #{tag.name}
        </h1>
        {posts.length ? (
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {posts.map((p) => (
              <BlogCard key={p.id} post={p} />
            ))}
          </div>
        ) : (
          <div className="mt-12">
            <EmptyState title="No posts with this tag" />
          </div>
        )}
        <BlogRecoveryCtas />
      </Container>
    </main>
  );
}
