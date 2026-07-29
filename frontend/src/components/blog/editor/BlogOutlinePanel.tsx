"use client";

import { extractOutline, type BlogContentDocument } from "@/lib/blog-document";

type Props = {
  document: BlogContentDocument;
  onNavigate: (blockId: string) => void;
};

export function BlogOutlinePanel({ document, onNavigate }: Props) {
  const outline = extractOutline(document.blocks);
  const h2Count = outline.filter((o) => o.level === 2).length;
  const dupes = outline
    .map((o) => o.text.toLowerCase())
    .filter((t, i, arr) => arr.indexOf(t) !== i);

  return (
    <div className="p-4 space-y-3 text-sm">
      <h3 className="font-medium">Article outline</h3>
      {h2Count === 0 ? (
        <p className="text-amber-600 text-xs">No H2 headings — add headings for structure and TOC.</p>
      ) : null}
      {dupes.length > 0 ? (
        <p className="text-amber-600 text-xs">Duplicate heading titles detected.</p>
      ) : null}
      <ol className="space-y-1">
        {outline.map((item) => (
          <li
            key={item.blockId}
            className={item.level === 3 ? "ml-4 text-muted" : ""}
          >
            <button
              type="button"
              className="text-left hover:text-primary w-full truncate"
              onClick={() => onNavigate(item.blockId)}
            >
              {item.text || "(empty)"}
            </button>
          </li>
        ))}
      </ol>
      {outline.length === 0 ? (
        <p className="text-muted text-xs">Headings appear here as you write.</p>
      ) : null}
    </div>
  );
}
