import Link from "next/link";

import type { HelpArticleListItem } from "@/lib/knowledge-base/api";

export function HelpArticleCard({
  article,
  featured = false,
}: {
  article: HelpArticleListItem;
  featured?: boolean;
}) {
  return (
    <Link
      href={`/help/articles/${article.slug}`}
      className={`group block transition-transform duration-300 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        featured ? "sm:col-span-2" : ""
      }`}
    >
      <article
        className={`h-full border-b border-border pb-6 ${
          featured ? "sm:pb-8" : ""
        }`}
      >
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          {article.category ? <span>{article.category.name}</span> : null}
          {article.content_type !== "text" ? (
            <>
              <span aria-hidden>·</span>
              <span className="text-primary-text">{article.content_type.replace("_", " ")}</span>
            </>
          ) : null}
          {article.video_url ? (
            <>
              <span aria-hidden>·</span>
              <span>Video</span>
            </>
          ) : null}
        </div>
        <h3
          className={`mt-2 font-display font-extrabold tracking-tight text-heading transition-colors group-hover:text-primary-text ${
            featured ? "text-2xl sm:text-3xl" : "text-lg sm:text-xl"
          }`}
        >
          {article.title}
        </h3>
        {article.excerpt ? (
          <p
            className={`mt-2 text-muted-foreground ${
              featured ? "max-w-2xl text-base sm:text-lg" : "text-sm sm:text-base"
            }`}
          >
            {article.excerpt}
          </p>
        ) : null}
        <p className="mt-3 text-xs font-semibold text-foreground/60">
          {article.reading_time_minutes} min read
          {article.helpful_count > 0
            ? ` · ${article.helpful_count} found helpful`
            : null}
        </p>
      </article>
    </Link>
  );
}
