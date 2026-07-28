/** Helpers for deriving / mutating markdown H2 sections in the studio editor. */

export type MarkdownSection = {
  index: number;
  heading: string;
  /** Full heading line including ## */
  headingLine: string;
  start: number;
  end: number;
  body: string;
  locked?: boolean;
};

const H2_RE = /^##\s+(.+)$/gm;

export function parseMarkdownH2Sections(markdown: string): MarkdownSection[] {
  const matches: Array<{ heading: string; headingLine: string; index: number }> =
    [];
  let m: RegExpExecArray | null;
  const re = new RegExp(H2_RE.source, "gm");
  while ((m = re.exec(markdown)) !== null) {
    matches.push({
      heading: m[1].trim(),
      headingLine: m[0],
      index: m.index,
    });
  }
  return matches.map((hit, i) => {
    const start = hit.index;
    const end =
      i + 1 < matches.length ? matches[i + 1].index : markdown.length;
    const chunk = markdown.slice(start, end);
    const firstNl = chunk.indexOf("\n");
    const body = firstNl >= 0 ? chunk.slice(firstNl + 1).replace(/\s+$/, "") : "";
    return {
      index: i,
      heading: hit.heading,
      headingLine: hit.headingLine,
      start,
      end,
      body,
    };
  });
}

export function replaceSectionAt(
  markdown: string,
  sectionIndex: number,
  next: { heading?: string; body?: string },
): string {
  const sections = parseMarkdownH2Sections(markdown);
  const sec = sections[sectionIndex];
  if (!sec) return markdown;
  const heading = next.heading ?? sec.heading;
  const body = next.body ?? sec.body;
  const replacement = `## ${heading}\n\n${body.trim()}\n\n`;
  return (
    markdown.slice(0, sec.start) + replacement + markdown.slice(sec.end)
  );
}

export function moveSection(
  markdown: string,
  fromIndex: number,
  direction: -1 | 1,
): string {
  const sections = parseMarkdownH2Sections(markdown);
  const toIndex = fromIndex + direction;
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= sections.length ||
    toIndex >= sections.length
  ) {
    return markdown;
  }
  const chunks = sections.map((s) =>
    markdown.slice(s.start, s.end).replace(/\s+$/, "") + "\n\n",
  );
  const tmp = chunks[fromIndex];
  chunks[fromIndex] = chunks[toIndex];
  chunks[toIndex] = tmp;
  const prefix =
    sections[0].start > 0
      ? markdown.slice(0, sections[0].start).replace(/\s+$/, "") + "\n\n"
      : "";
  const suffixStart = sections[sections.length - 1].end;
  const suffix = markdown.slice(suffixStart);
  return (prefix + chunks.join("") + suffix).replace(/\n{3,}/g, "\n\n");
}

export function deleteSection(markdown: string, sectionIndex: number): string {
  const sections = parseMarkdownH2Sections(markdown);
  const sec = sections[sectionIndex];
  if (!sec) return markdown;
  return (markdown.slice(0, sec.start) + markdown.slice(sec.end)).replace(
    /\n{3,}/g,
    "\n\n",
  );
}

export function duplicateSection(
  markdown: string,
  sectionIndex: number,
): string {
  const sections = parseMarkdownH2Sections(markdown);
  const sec = sections[sectionIndex];
  if (!sec) return markdown;
  const chunk = markdown.slice(sec.start, sec.end).replace(/\s+$/, "") + "\n\n";
  return (
    markdown.slice(0, sec.end) + chunk + markdown.slice(sec.end)
  ).replace(/\n{3,}/g, "\n\n");
}

export function insertSectionBelow(
  markdown: string,
  sectionIndex: number,
  heading = "New section",
): string {
  const sections = parseMarkdownH2Sections(markdown);
  const sec = sections[sectionIndex];
  const block = `## ${heading}\n\nWrite this section…\n\n`;
  if (!sec) {
    return `${markdown.trim()}\n\n${block}`;
  }
  return (
    markdown.slice(0, sec.end) + block + markdown.slice(sec.end)
  ).replace(/\n{3,}/g, "\n\n");
}

export function outlineToMarkdown(outline: {
  sections: Array<{ heading: string; key_point?: string }>;
  introduction_purpose?: string;
  conclusion_direction?: string;
}): string {
  const parts: string[] = [];
  if (outline.introduction_purpose) {
    parts.push(outline.introduction_purpose.trim());
  }
  for (const s of outline.sections) {
    parts.push(
      `## ${s.heading}\n\n${s.key_point?.trim() || "Write this section…"}\n`,
    );
  }
  if (outline.conclusion_direction) {
    parts.push(
      `## Conclusion\n\n${outline.conclusion_direction.trim()}\n`,
    );
  }
  return parts.join("\n").trim() + "\n";
}

/** Lightweight markdown → HTML for in-studio preview (not public indexable). */
export function simpleMarkdownToHtml(md: string): string {
  const escape = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let inUl = false;
  let inOl = false;
  let inCode = false;
  let codeBuf: string[] = [];

  const closeLists = () => {
    if (inUl) {
      out.push("</ul>");
      inUl = false;
    }
    if (inOl) {
      out.push("</ol>");
      inOl = false;
    }
  };

  const inline = (s: string) =>
    escape(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" rel="noopener noreferrer">$1</a>',
      );

  for (const raw of lines) {
    if (raw.startsWith("```")) {
      if (inCode) {
        out.push(`<pre><code>${escape(codeBuf.join("\n"))}</code></pre>`);
        codeBuf = [];
        inCode = false;
      } else {
        closeLists();
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeBuf.push(raw);
      continue;
    }
    if (/^\s*$/.test(raw)) {
      closeLists();
      continue;
    }
    if (/^###\s+/.test(raw)) {
      closeLists();
      out.push(`<h3>${inline(raw.replace(/^###\s+/, ""))}</h3>`);
      continue;
    }
    if (/^##\s+/.test(raw)) {
      closeLists();
      out.push(`<h2>${inline(raw.replace(/^##\s+/, ""))}</h2>`);
      continue;
    }
    if (/^#\s+/.test(raw)) {
      closeLists();
      out.push(`<h1>${inline(raw.replace(/^#\s+/, ""))}</h1>`);
      continue;
    }
    if (/^>\s?/.test(raw)) {
      closeLists();
      out.push(`<blockquote><p>${inline(raw.replace(/^>\s?/, ""))}</p></blockquote>`);
      continue;
    }
    if (/^[-*]\s+/.test(raw)) {
      if (!inUl) {
        closeLists();
        out.push("<ul>");
        inUl = true;
      }
      out.push(`<li>${inline(raw.replace(/^[-*]\s+/, ""))}</li>`);
      continue;
    }
    if (/^\d+\.\s+/.test(raw)) {
      if (!inOl) {
        closeLists();
        out.push("<ol>");
        inOl = true;
      }
      out.push(`<li>${inline(raw.replace(/^\d+\.\s+/, ""))}</li>`);
      continue;
    }
    closeLists();
    out.push(`<p>${inline(raw)}</p>`);
  }
  closeLists();
  if (inCode) {
    out.push(`<pre><code>${escape(codeBuf.join("\n"))}</code></pre>`);
  }
  return out.join("\n");
}
