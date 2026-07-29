"use client";

import { BlogDocumentRenderer } from "@/components/blog/editor/BlogBlockRenderer";
import type { BlogContentDocument, PreviewDevice, PreviewTheme } from "@/lib/blog-document";

type Props = {
  document: BlogContentDocument;
  title: string;
  excerpt: string;
  device: PreviewDevice;
  theme: PreviewTheme;
  bodyHtml?: string | null;
};

export function BlogResponsivePreview({
  document,
  title,
  excerpt,
  device,
  theme,
  bodyHtml,
}: Props) {
  const widthClass =
    device === "mobile"
      ? "max-w-[390px]"
      : device === "tablet"
        ? "max-w-[768px]"
        : "max-w-[1024px]";

  const themeClass =
    theme === "dark" ? "dark" : theme === "light" ? "" : "";

  return (
    <div
      className={`mx-auto border border-border rounded-[var(--radius-md)] bg-background overflow-hidden ${widthClass} ${themeClass}`}
      data-preview-noindex
    >
      <div className="bg-amber-500/10 text-amber-800 dark:text-amber-200 text-xs px-3 py-1 text-center">
        Draft preview — not indexed
      </div>
      <div className="p-6 space-y-4">
        <h1 className="font-display text-2xl font-bold">{title || "Untitled"}</h1>
        {excerpt ? <p className="text-muted">{excerpt}</p> : null}
        {bodyHtml ? (
          <div
            className="blog-prose max-w-none dark:prose-invert"
            dangerouslySetInnerHTML={{ __html: bodyHtml }}
          />
        ) : (
          <BlogDocumentRenderer blocks={document.blocks} />
        )}
      </div>
    </div>
  );
}
