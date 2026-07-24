import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { BlogCard } from "@/components/blog/BlogCard";
import { BlogRecoveryCtas } from "@/components/blog/BlogRecoveryCtas";
import { Container, EmptyState } from "@/components/ui";
import type { BlogAuthor } from "@/lib/blog-api";
import {
  fetchBlogPostsServer,
  fetchBlogTaxonomyServer,
} from "@/lib/blog-api";
import { buildPageMetadata } from "@/lib/seo/site";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const author = (await fetchBlogTaxonomyServer(
    "authors",
    slug,
  )) as BlogAuthor | null;
  if (!author) return { title: "Author", robots: { index: false } };
  return buildPageMetadata({
    title: `${author.display_name} · Blog`,
    description: author.bio || `Posts by ${author.display_name} on Pàdéyá.`,
    path: `/blog/author/${slug}`,
  });
}

export const revalidate = 300;

export default async function BlogAuthorPage({ params }: Props) {
  const { slug } = await params;
  const author = (await fetchBlogTaxonomyServer(
    "authors",
    slug,
  )) as BlogAuthor | null;
  if (!author) notFound();
  const posts = await fetchBlogPostsServer({ author: slug });

  return (
    <main className="bg-background pb-20 pt-10">
      <Container>
        <div className="flex items-start gap-4">
          {author.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={author.avatar_url}
              alt=""
              className="h-16 w-16 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-ink font-display text-xl font-bold text-paper">
              {author.display_name.slice(0, 1)}
            </div>
          )}
          <div>
            <h1 className="font-display text-3xl font-extrabold tracking-tight">
              {author.display_name}
            </h1>
            {author.role_title ? (
              <p className="mt-1 text-sm text-primary">{author.role_title}</p>
            ) : null}
            {author.bio ? (
              <p className="mt-3 max-w-xl text-muted-foreground">{author.bio}</p>
            ) : null}
          </div>
        </div>
        {posts.length ? (
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {posts.map((p) => (
              <BlogCard key={p.id} post={p} />
            ))}
          </div>
        ) : (
          <div className="mt-12">
            <EmptyState title="No posts from this author yet" />
          </div>
        )}
        <BlogRecoveryCtas />
      </Container>
    </main>
  );
}
