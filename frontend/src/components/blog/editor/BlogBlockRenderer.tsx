"use client";

import { simpleMarkdownToHtml } from "@/components/blog/studio/markdown-utils";
import type { BlogBlock } from "@/lib/blog-document";

type Props = {
  block: BlogBlock;
  preview?: boolean;
  onNavigate?: (anchor: string) => void;
};

function RichContent({ block }: { block: BlogBlock }) {
  const html = String(block.content.html || "");
  const md = String(block.content.markdown || "");
  if (html) {
    return (
      <div
        className="blog-prose prose-sm max-w-none dark:prose-invert"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }
  if (md) {
    return (
      <div
        className="blog-prose prose-sm max-w-none dark:prose-invert"
        dangerouslySetInnerHTML={{ __html: simpleMarkdownToHtml(md) }}
      />
    );
  }
  return <p className="text-muted text-sm italic">Empty block</p>;
}

export function BlogBlockRenderer({ block }: Props) {
  if (block.props.visible === false) return null;

  const widthClass =
    block.props.content_width === "narrow"
      ? "max-w-prose mx-auto"
      : block.props.content_width === "wide"
        ? "max-w-5xl mx-auto"
        : block.props.content_width === "full"
          ? "w-full"
          : "max-w-3xl mx-auto";

  const spacingClass =
    block.props.spacing === "compact"
      ? "py-2"
      : block.props.spacing === "spacious"
        ? "py-12"
        : block.props.spacing === "none"
          ? "py-0"
          : "py-6";

  switch (block.type) {
    case "rich_text":
    case "legacy_rich_text":
      return (
        <div className={widthClass}>
          <RichContent block={block} />
        </div>
      );
    case "heading": {
      const level = Number(block.content.level || 2);
      const Tag = level === 3 ? "h3" : "h2";
      return (
        <Tag className={`font-display font-semibold ${widthClass}`}>
          {String(block.content.text || "")}
        </Tag>
      );
    }
    case "image":
      return (
        <figure className={`${widthClass} ${spacingClass}`}>
          {block.content.url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={String(block.content.url)}
              alt={String(block.content.alt || "")}
              className="rounded-[var(--radius-md)] w-full"
            />
          ) : (
            <div className="h-40 bg-surface border border-border rounded-[var(--radius-md)] flex items-center justify-center text-muted text-sm">
              No image
            </div>
          )}
          {block.content.caption ? (
            <figcaption className="text-sm text-muted mt-2">
              {String(block.content.caption)}
            </figcaption>
          ) : null}
        </figure>
      );
    case "quote":
      return (
        <blockquote
          className={`border-l-4 border-primary pl-4 italic text-muted ${widthClass} ${spacingClass}`}
        >
          {String(block.content.text || "")}
          {block.content.attribution ? (
            <cite className="block not-italic text-sm mt-2">
              — {String(block.content.attribution)}
            </cite>
          ) : null}
        </blockquote>
      );
    case "cta":
      return (
        <div className={`blog-cta ${widthClass} ${spacingClass}`}>
          <a
            href={String(block.content.href || "/events")}
            className="blog-cta-btn inline-flex items-center rounded-[var(--radius-md)] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            {String(block.content.label || "Learn more")}
          </a>
        </div>
      );
    case "divider":
      return <hr className="border-border my-6" />;
    case "spacer":
      return <div className="h-8" aria-hidden />;
    case "faq": {
      const items = (block.content.items as Array<{ question: string; answer: string }>) || [];
      return (
        <div className={`space-y-2 ${widthClass} ${spacingClass}`}>
          {items.map((item, i) => (
            <details key={i} className="rounded-[var(--radius-md)] border border-border p-3">
              <summary className="cursor-pointer font-medium">{item.question}</summary>
              <div
                className="mt-2 text-sm text-muted blog-prose"
                dangerouslySetInnerHTML={{
                  __html: simpleMarkdownToHtml(item.answer || ""),
                }}
              />
            </details>
          ))}
        </div>
      );
    }
    case "table": {
      const headers = (block.content.headers as string[]) || [];
      const rows = (block.content.rows as string[][]) || [];
      return (
        <div className={`overflow-x-auto ${widthClass} ${spacingClass}`}>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr>
                {headers.map((h, i) => (
                  <th key={i} className="border border-border p-2 text-left bg-surface">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => (
                    <td key={ci} className="border border-border p-2">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    case "list": {
      const items = (block.content.items as string[]) || [];
      const Tag = block.content.ordered ? "ol" : "ul";
      return (
        <Tag className={`list-disc list-inside space-y-1 ${widthClass} ${spacingClass}`}>
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </Tag>
      );
    }
    case "tip":
    case "warning":
    case "key_takeaway":
    case "important_note":
    case "author_note":
      return (
        <div
          className={`rounded-[var(--radius-md)] border border-border bg-surface p-4 ${widthClass} ${spacingClass}`}
        >
          <RichContent block={block} />
        </div>
      );
    case "table_of_contents":
      return (
        <nav className={`${widthClass} ${spacingClass} text-sm`} aria-label="Table of contents">
          <p className="font-medium mb-2">On this page</p>
          <p className="text-muted italic">Generated from headings when published.</p>
        </nav>
      );
    case "two_column_row":
    case "three_column_row":
      return (
        <div
          className={`grid gap-4 ${block.type === "three_column_row" ? "md:grid-cols-3" : "md:grid-cols-2"} ${spacingClass}`}
        >
          {(block.children || []).map((col) => (
            <div key={col.id} className="space-y-4">
              {(col.children || []).map((child) => (
                <BlogBlockRenderer key={child.id} block={child} />
              ))}
            </div>
          ))}
        </div>
      );
    case "standard_section":
    case "full_width_section":
    case "narrow_section":
    case "section":
      return (
        <section className={`${spacingClass} ${widthClass}`}>
          {(block.children || []).map((child) => (
            <BlogBlockRenderer key={child.id} block={child} />
          ))}
        </section>
      );
    default:
      return (
        <div className={`blog-block-unknown ${widthClass} ${spacingClass}`}>
          <span className="sr-only">Unsupported block type: {block.type}</span>
          [{block.type}]
        </div>
      );
  }
}

export function BlogDocumentRenderer({ blocks }: { blocks: BlogBlock[] }) {
  return (
    <article className="blog-document space-y-4">
      {blocks.map((block) => (
        <BlogBlockRenderer key={block.id} block={block} />
      ))}
    </article>
  );
}
