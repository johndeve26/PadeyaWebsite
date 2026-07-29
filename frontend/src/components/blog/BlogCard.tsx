"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

import type { BlogPostListItem } from "@/lib/blog-api";
import {
  trackBlogCardClick,
  trackBlogCardImpression,
} from "@/lib/analytics";
import {
  blogCategoryGradient,
  blogCoverAlt,
  resolveBlogCoverUrl,
} from "@/lib/blog-cover";
import { brand } from "@/lib/brand";

function formatDate(iso?: string | null) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

export function BlogCard({
  post,
  featured = false,
  listContext = "blog_index",
  cardPosition,
}: {
  post: BlogPostListItem;
  featured?: boolean;
  listContext?: string;
  cardPosition?: number;
}) {
  const date = formatDate(post.published_at);
  const { src, isPlaceholder } = resolveBlogCoverUrl(
    post.cover_url,
    post.category,
  );
  const alt = blogCoverAlt(post.title, post.category);
  const rootRef = useRef<HTMLElement | null>(null);
  const impressed = useRef(false);

  useEffect(() => {
    const el = rootRef.current;
    if (!el || impressed.current) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const hit = entries.some(
          (e) => e.isIntersecting && e.intersectionRatio >= 0.5,
        );
        if (!hit || impressed.current) return;
        impressed.current = true;
        trackBlogCardImpression({
          postId: post.id,
          slug: post.slug,
          listContext,
          cardPosition,
        });
        obs.disconnect();
      },
      { threshold: 0.5 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [post.id, post.slug, listContext, cardPosition]);

  return (
    <article
      ref={rootRef}
      className={
        featured
          ? "group relative overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)]"
          : "group flex flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card transition duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-[var(--shadow)]"
      }
    >
      <Link
        href={`/blog/${post.slug}`}
        className="flex h-full flex-col"
        onClick={() =>
          trackBlogCardClick({
            postId: post.id,
            slug: post.slug,
            listContext,
          })
        }
      >
        <div
          className={
            featured
              ? "relative aspect-[21/9] bg-ink sm:aspect-[2.4/1]"
              : "relative aspect-[16/10] bg-ink"
          }
          style={
            isPlaceholder
              ? { background: blogCategoryGradient(post.category) }
              : undefined
          }
        >
          {src ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={src}
              alt={alt}
              className={
                isPlaceholder
                  ? "h-full w-full object-cover opacity-90 transition duration-500 group-hover:scale-[1.03]"
                  : "h-full w-full object-cover opacity-95 transition duration-500 group-hover:scale-[1.03]"
              }
            />
          ) : (
            <div className="flex h-full items-end p-6">
              <span className="font-display text-2xl font-extrabold text-paper">
                {post.title.slice(0, 1)}
              </span>
            </div>
          )}
          {post.is_featured ? (
            <span
              className="absolute left-3 top-3 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-ink"
              style={{ background: brand.colors.green }}
            >
              Featured
            </span>
          ) : null}
        </div>
        <div className="flex flex-1 flex-col gap-2.5 p-5">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {post.category ? (
              <span className="font-semibold text-primary-text">
                {post.category.name}
              </span>
            ) : null}
            {date ? <span>· {date}</span> : null}
            <span>· {post.reading_time_minutes} min read</span>
          </div>
          <h2
            className={
              featured
                ? "font-display text-2xl font-extrabold tracking-tight text-heading sm:text-3xl"
                : "font-display text-lg font-bold tracking-tight text-heading"
            }
          >
            {post.title}
          </h2>
          {post.excerpt ? (
            <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
              {post.excerpt}
            </p>
          ) : null}
          <span className="mt-auto pt-3 text-sm font-semibold text-primary-text transition-colors group-hover:underline">
            Read more →
          </span>
        </div>
      </Link>
    </article>
  );
}
