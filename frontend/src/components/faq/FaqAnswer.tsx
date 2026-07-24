import Link from "next/link";
import { Fragment, type ReactNode } from "react";

const LINK_RE = /\[([^\]]+)\]\(([^)]+)\)/g;

/** Renders FAQ answers with optional markdown-style [label](/path) links. */
export function FaqAnswer({ text }: { text: string }) {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  const re = new RegExp(LINK_RE.source, "g");

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const label = match[1];
    const href = match[2];
    nodes.push(
      <Link
        key={`${href}-${match.index}`}
        href={href}
        className="font-semibold text-primary-text underline-offset-2 hover:underline"
      >
        {label}
      </Link>,
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return (
    <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted-foreground sm:mt-5 sm:text-base">
      {nodes.map((node, i) => (
        <Fragment key={i}>{node}</Fragment>
      ))}
    </p>
  );
}
