"use client";

import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Safe absolute http(s) or same-origin relative paths only. */
function safeHref(raw: string): string | null {
  const href = raw.trim();
  if (!href) return null;
  if (href.startsWith("/") && !href.startsWith("//")) return href;
  try {
    const url = new URL(href);
    if (url.protocol === "http:" || url.protocol === "https:") return url.href;
  } catch {
    return null;
  }
  return null;
}

/**
 * Strip HTML tags from model output (never render raw HTML).
 * React text nodes are already XSS-safe; this only removes tag-looking markup.
 */
function stripHtmlTags(input: string): string {
  return input.replace(/<\/?[a-zA-Z][^>]*>/g, "");
}

type Segment =
  | { type: "text"; value: string }
  | { type: "bold"; value: string }
  | { type: "italic"; value: string }
  | { type: "code"; value: string }
  | { type: "link"; label: string; href: string };

function parseInline(text: string): Segment[] {
  const segments: Segment[] = [];
  const re =
    /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      segments.push({ type: "text", value: text.slice(last, match.index) });
    }
    const token = match[0];
    if (token.startsWith("**")) {
      segments.push({ type: "bold", value: token.slice(2, -2) });
    } else if (token.startsWith("`")) {
      segments.push({ type: "code", value: token.slice(1, -1) });
    } else if (token.startsWith("[")) {
      const m = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (m) {
        const href = safeHref(m[2]);
        if (href) {
          segments.push({ type: "link", label: m[1], href });
        } else {
          segments.push({ type: "text", value: m[1] });
        }
      }
    } else if (token.startsWith("*")) {
      segments.push({ type: "italic", value: token.slice(1, -1) });
    }
    last = match.index + token.length;
  }
  if (last < text.length) {
    segments.push({ type: "text", value: text.slice(last) });
  }
  return segments;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return parseInline(text).map((seg, i) => {
    const key = `${keyPrefix}-${i}`;
    switch (seg.type) {
      case "bold":
        return (
          <strong key={key} className="font-semibold">
            {seg.value}
          </strong>
        );
      case "italic":
        return <em key={key}>{seg.value}</em>;
      case "code":
        return (
          <code
            key={key}
            className="rounded-[var(--radius-sm)] bg-surface-muted px-1 py-0.5 font-mono text-[0.85em] dark:bg-surface-elevated"
          >
            {seg.value}
          </code>
        );
      case "link":
        return (
          <a
            key={key}
            href={seg.href}
            className="font-semibold text-primary-text underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
            rel={seg.href.startsWith("http") ? "noopener noreferrer" : undefined}
            target={seg.href.startsWith("http") ? "_blank" : undefined}
          >
            {seg.label}
          </a>
        );
      default:
        return <span key={key}>{seg.value}</span>;
    }
  });
}

function linkifyBareUrls(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(https?:\/\/[^\s<>"')\]]+)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(...renderInline(text.slice(last, match.index), `t${i++}`));
    }
    const href = safeHref(match[1]);
    if (href) {
      parts.push(
        <a
          key={`u${i++}`}
          href={href}
          className="font-semibold text-primary-text underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
          rel="noopener noreferrer"
          target="_blank"
        >
          {match[1]}
        </a>,
      );
    } else {
      parts.push(<span key={`u${i++}`}>{match[1]}</span>);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    parts.push(...renderInline(text.slice(last), `t${i++}`));
  }
  return parts;
}

/**
 * Safe Markdown renderer — typed React only, no raw HTML / dangerouslySetInnerHTML.
 */
export function AssistantMarkdown({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  const text = stripHtmlTags(content);
  const blocks = text.split(/\n{2,}/);

  return (
    <div
      className={cn(
        "space-y-2 text-sm leading-relaxed break-words [&_a]:break-all",
        className,
      )}
    >
      {blocks.map((block, bi) => {
        const lines = block.split("\n");
        const isList =
          lines.every(
            (l) =>
              !l.trim() ||
              /^[-*]\s+/.test(l.trim()) ||
              /^\d+\.\s+/.test(l.trim()),
          ) &&
          lines.some(
            (l) =>
              /^[-*]\s+/.test(l.trim()) || /^\d+\.\s+/.test(l.trim()),
          );

        if (isList) {
          return (
            <ul key={bi} className="list-disc space-y-1 pl-4">
              {lines
                .map((l) => l.trim())
                .filter(Boolean)
                .map((l, li) => {
                  const item = l
                    .replace(/^[-*]\s+/, "")
                    .replace(/^\d+\.\s+/, "");
                  return <li key={li}>{linkifyBareUrls(item)}</li>;
                })}
            </ul>
          );
        }

        return (
          <p key={bi} className="whitespace-pre-wrap">
            {lines.map((line, li) => (
              <span key={li}>
                {li > 0 ? <br /> : null}
                {linkifyBareUrls(line)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
