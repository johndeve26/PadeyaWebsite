/**
 * Safe inline markdown parsing for Pàdéyá Copilot (no raw HTML).
 */

export type MarkdownSegment =
  | { type: "text"; value: string }
  | { type: "bold"; value: string }
  | { type: "italic"; value: string }
  | { type: "code"; value: string }
  | { type: "link"; label: string; href: string };

export type MarkdownBlock =
  | { type: "text"; value: string }
  | { type: "link"; label: string; href: string; raw: string };

/** Safe absolute http(s) or same-origin relative paths only. */
export function safeAssistantHref(raw: string): string | null {
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

export function stripAssistantHtmlTags(input: string): string {
  return input.replace(/<\/?[a-zA-Z][^>]*>/g, "");
}

const MD_LINK_RE = /\[([^\]]+)\]\(([^)]+)\)/g;

/**
 * Split text into plain segments and markdown `[label](url)` links.
 * Markdown links are parsed before bare URL linkification so URLs inside
 * `(…)` are not treated as standalone links.
 */
export function splitMarkdownLinks(text: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  MD_LINK_RE.lastIndex = 0;
  while ((match = MD_LINK_RE.exec(text)) !== null) {
    if (match.index > last) {
      blocks.push({ type: "text", value: text.slice(last, match.index) });
    }
    blocks.push({
      type: "link",
      label: match[1],
      href: match[2],
      raw: match[0],
    });
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    blocks.push({ type: "text", value: text.slice(last) });
  }
  if (!blocks.length && text) {
    blocks.push({ type: "text", value: text });
  }
  return blocks;
}

/** Bold, italic, and inline code — not markdown links (handled separately). */
export function parseInlineFormatting(text: string): MarkdownSegment[] {
  const segments: MarkdownSegment[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
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

const BARE_URL_RE = /(https?:\/\/[^\s<>"')\]]+)/g;

/**
 * Split plain text into formatting segments and bare http(s) URLs.
 */
export function parseTextWithBareUrls(text: string): MarkdownSegment[] {
  const segments: MarkdownSegment[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  BARE_URL_RE.lastIndex = 0;
  while ((match = BARE_URL_RE.exec(text)) !== null) {
    if (match.index > last) {
      segments.push(...parseInlineFormatting(text.slice(last, match.index)));
    }
    const href = safeAssistantHref(match[1]);
    if (href) {
      segments.push({ type: "link", label: match[1], href });
    } else {
      segments.push({ type: "text", value: match[1] });
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    segments.push(...parseInlineFormatting(text.slice(last)));
  }
  if (!segments.length && text) {
    segments.push(...parseInlineFormatting(text));
  }
  return segments;
}

/** Full inline parse: markdown links first, then bare URLs + formatting. */
export function parseAssistantInline(text: string): MarkdownSegment[] {
  const segments: MarkdownSegment[] = [];
  for (const block of splitMarkdownLinks(text)) {
    if (block.type === "link") {
      const href = safeAssistantHref(block.href);
      if (href) {
        segments.push({ type: "link", label: block.label, href });
      } else {
        segments.push({ type: "text", value: block.label });
      }
      continue;
    }
    segments.push(...parseTextWithBareUrls(block.value));
  }
  return segments;
}
