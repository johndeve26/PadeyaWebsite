import { withHeadingIds } from "@/lib/blog-heading-ids";

const proseClass =
  "blog-prose min-w-0 max-w-3xl text-[1.075rem] leading-[1.8] text-foreground/90 sm:text-lg sm:leading-[1.8] " +
  "[&_a]:font-semibold [&_a]:text-primary-text [&_a]:underline-offset-4 hover:[&_a]:underline " +
  "[&_blockquote]:my-8 [&_blockquote]:rounded-[var(--radius-md)] [&_blockquote]:border-l-[3px] [&_blockquote]:border-primary " +
  "[&_blockquote]:bg-[color-mix(in_srgb,var(--primary)_8%,var(--surface-muted))] [&_blockquote]:py-4 [&_blockquote]:pl-5 [&_blockquote]:pr-5 " +
  "[&_blockquote]:not-italic [&_blockquote]:text-foreground/85 [&_blockquote_p]:my-0 [&_blockquote_p]:leading-relaxed " +
  "[&_h2]:mt-14 [&_h2]:scroll-mt-28 [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-extrabold [&_h2]:tracking-tight [&_h2]:text-heading sm:[&_h2]:text-[1.85rem] " +
  "[&_h3]:mt-9 [&_h3]:scroll-mt-28 [&_h3]:font-display [&_h3]:text-xl [&_h3]:font-bold [&_h3]:text-heading " +
  "[&_hr]:my-10 [&_hr]:border-border " +
  "[&_img]:my-9 [&_img]:rounded-[var(--radius-lg)] [&_img]:border [&_img]:border-border [&_img]:shadow-[var(--shadow-soft)] " +
  "[&_li]:my-2 [&_li]:marker:text-primary " +
  "[&_ol]:my-6 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-6 " +
  "[&_p]:my-5 [&_p]:text-pretty " +
  "[&_pre]:my-8 [&_pre]:overflow-x-auto [&_pre]:rounded-[var(--radius-lg)] [&_pre]:border [&_pre]:border-paper/10 [&_pre]:bg-ink [&_pre]:p-5 [&_pre]:text-sm [&_pre]:text-paper " +
  "[&_strong]:font-bold [&_strong]:text-heading " +
  "[&_ul]:my-6 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6 " +
  "[&_.blog-cta]:my-10 [&_.blog-cta]:rounded-[var(--radius-lg)] [&_.blog-cta]:border [&_.blog-cta]:border-primary/25 " +
  "[&_.blog-cta]:bg-gradient-to-r [&_.blog-cta]:from-[color-mix(in_srgb,var(--primary)_12%,transparent)] [&_.blog-cta]:to-transparent " +
  "[&_.blog-cta]:px-5 [&_.blog-cta]:py-5 " +
  "[&_.blog-cta-btn]:inline-flex [&_.blog-cta-btn]:items-center [&_.blog-cta-btn]:rounded-[var(--radius-md)] " +
  "[&_.blog-cta-btn]:bg-primary [&_.blog-cta-btn]:px-5 [&_.blog-cta-btn]:py-2.5 [&_.blog-cta-btn]:text-sm [&_.blog-cta-btn]:font-bold " +
  "[&_.blog-cta-btn]:text-primary-foreground [&_.blog-cta-btn]:no-underline [&_.blog-cta-btn]:shadow-[var(--shadow-soft)] " +
  "hover:[&_.blog-cta-btn]:bg-primary-hover";

/** Renders sanitized server HTML for a blog article (prose only). */
export function BlogArticleBody({ html }: { html: string }) {
  const withIds = withHeadingIds(html);
  return (
    <article
      className={proseClass}
      dangerouslySetInnerHTML={{ __html: withIds }}
    />
  );
}

export function blogArticleHtmlWithIds(html: string): string {
  return withHeadingIds(html);
}
