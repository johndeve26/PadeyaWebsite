"use client";

import Link from "next/link";

import type { BlogPostListItem } from "@/lib/blog-api";
import { trackBlogRelatedClick } from "@/lib/analytics";
import {
  blogCategoryGradient,
  blogCoverAlt,
  resolveBlogCoverUrl,
} from "@/lib/blog-cover";

export function RelatedBlogCard({
  post,
  fromPostId,
}: {
  post: BlogPostListItem;
  fromPostId: string;
}) {
  const { src, isPlaceholder } = resolveBlogCoverUrl(
    post.cover_url,
    post.category,
  );
  const alt = blogCoverAlt(post.title, post.category);

  return (
    <Link
      href={`/blog/${post.slug}`}
      className="group flex flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card transition hover:border-primary/40"
      onClick={() =>
        trackBlogRelatedClick({
          postId: fromPostId,
          relatedPostId: post.id,
          relatedSlug: post.slug,
        })
      }
    >
      <div
        className="relative aspect-[16/10] bg-ink"
        style={
          isPlaceholder
            ? { background: blogCategoryGradient(post.category) }
            : undefined
        }
      >
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={alt} className="h-full w-full object-cover" />
        ) : null}
      </div>
      <div className="space-y-1 p-4">
        <h3 className="font-display text-base font-bold text-heading group-hover:underline">
          {post.title}
        </h3>
        {post.excerpt ? (
          <p className="line-clamp-2 text-sm text-muted-foreground">
            {post.excerpt}
          </p>
        ) : null}
      </div>
    </Link>
  );
}
