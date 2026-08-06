"use client";

import { type ReactNode } from "react";

import { cn } from "@/lib/cn";
import {
  parseAssistantInline,
  stripAssistantHtmlTags,
  type MarkdownSegment,
} from "@/lib/assistant/markdown-parse";

function renderSegments(segments: MarkdownSegment[], keyPrefix: string): ReactNode[] {
  return segments.map((seg, i) => {
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

function renderRichInline(text: string, keyPrefix: string): ReactNode[] {
  return renderSegments(parseAssistantInline(text), keyPrefix);
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
  const text = stripAssistantHtmlTags(content);
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
                  return <li key={li}>{renderRichInline(item, `li-${bi}-${li}`)}</li>;
                })}
            </ul>
          );
        }

        return (
          <p key={bi} className="whitespace-pre-wrap">
            {lines.map((line, li) => (
              <span key={li}>
                {li > 0 ? <br /> : null}
                {renderRichInline(line, `p-${bi}-${li}`)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
