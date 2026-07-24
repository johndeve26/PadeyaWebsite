/** Inject heading ids into HTML for TOC anchors (server-safe). */
export function withHeadingIds(html: string): string {
  return html.replace(
    /<h([23])([^>]*)>(.*?)<\/h\1>/gi,
    (_all, level, attrs, inner) => {
      const text = String(inner)
        .replace(/<[^>]+>/g, "")
        .trim();
      const id = text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      if (/id=/.test(attrs)) {
        return `<h${level}${attrs}>${inner}</h${level}>`;
      }
      return `<h${level}${attrs} id="${id}">${inner}</h${level}>`;
    },
  );
}
