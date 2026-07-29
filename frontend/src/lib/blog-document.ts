/** Canonical blog content document types — shared by Standard Editor and Layout Manager. */

export const DOCUMENT_VERSION = 1;

export type ContentWidth = "narrow" | "standard" | "wide" | "full";
export type SpacingPreset = "none" | "compact" | "normal" | "spacious";
export type EditorMode = "standard" | "layout";
export type HeroVariant =
  | "standard"
  | "image_led"
  | "minimal"
  | "split"
  | "editorial"
  | "none";

export type BlogDocumentSettings = {
  content_width: ContentWidth;
  show_table_of_contents: boolean;
  sticky_table_of_contents: boolean;
  reading_progress: boolean;
};

export type BlockProps = {
  content_width?: ContentWidth;
  alignment?: "left" | "center" | "right";
  background?: "default" | "muted" | "primary_subtle" | "surface" | "elevated";
  spacing?: SpacingPreset;
  padding_top?: string;
  padding_bottom?: string;
  locked?: boolean;
  movable_when_locked?: boolean;
  visible?: boolean;
  include_in_toc?: boolean;
  anchor_id?: string;
  mobile_stack_order?: string;
  variant?: string;
  [key: string]: unknown;
};

export type BlogBlock = {
  id: string;
  type: string;
  variant: string;
  props: BlockProps;
  content: Record<string, unknown>;
  children: BlogBlock[];
};

export type BlogContentDocument = {
  version: number;
  settings: BlogDocumentSettings;
  blocks: BlogBlock[];
};

export type HeroSettings = {
  variant: HeroVariant;
  focal_x?: number;
  focal_y?: number;
  show_reading_time?: boolean;
  show_author?: boolean;
  show_date?: boolean;
};

export type LayoutTemplate = {
  id?: string;
  name: string;
  slug: string;
  description?: string | null;
  category?: string;
  document: BlogContentDocument;
  hero_settings?: HeroSettings | null;
  is_builtin?: boolean;
};

export type ReusableSection = {
  id?: string;
  name: string;
  slug: string;
  description?: string | null;
  section: BlogBlock;
};

export type PreviewDevice = "desktop" | "tablet" | "mobile";
export type PreviewTheme = "light" | "dark" | "system";

export type ContentMode = "legacy" | "block_document";

/** Block types with full public renderer + editor support. */
export const INSERTABLE_BLOCK_TYPES = [
  "rich_text",
  "heading",
  "image",
  "quote",
  "list",
  "table",
  "faq",
  "cta",
  "divider",
  "spacer",
  "tip",
  "warning",
  "key_takeaway",
  "important_note",
  "author_note",
  "table_of_contents",
  "standard_section",
  "full_width_section",
  "narrow_section",
  "two_column_row",
] as const;

export function isLegacyDocument(doc: BlogContentDocument | null | undefined): boolean {
  if (!doc) return true;
  const blocks = doc.blocks || [];
  return blocks.length === 1 && blocks[0]?.type === "legacy_rich_text";
}

export function isBlockDocumentMode(
  doc: BlogContentDocument | null | undefined,
  contentMode?: ContentMode | null,
): boolean {
  if (contentMode === "block_document") return true;
  if (contentMode === "legacy") return false;
  if (!doc) return false;
  return !isLegacyDocument(doc);
}

export function resolveContentMode(
  doc: BlogContentDocument | null | undefined,
  contentMode?: ContentMode | null,
): ContentMode {
  if (contentMode) return contentMode;
  return isBlockDocumentMode(doc) ? "block_document" : "legacy";
}

export const BLOCK_CATEGORIES = {
  content: INSERTABLE_BLOCK_TYPES.filter((t) =>
    ["rich_text", "heading", "image", "quote", "list", "table", "faq", "divider", "spacer"].includes(
      t,
    ),
  ),
  editorial: INSERTABLE_BLOCK_TYPES.filter((t) =>
    ["tip", "warning", "key_takeaway", "important_note", "author_note", "table_of_contents"].includes(
      t,
    ),
  ),
  marketing: ["cta"] as const,
  layout: INSERTABLE_BLOCK_TYPES.filter((t) =>
    ["standard_section", "full_width_section", "narrow_section", "two_column_row"].includes(t),
  ),
} as const;

export const SLASH_COMMANDS = [
  { command: "heading", label: "Heading", type: "heading" },
  { command: "image", label: "Image", type: "image" },
  { command: "gallery", label: "Gallery", type: "image_gallery" },
  { command: "quote", label: "Quote", type: "quote" },
  { command: "callout", label: "Tip callout", type: "tip" },
  { command: "cta", label: "CTA", type: "cta" },
  { command: "columns", label: "Two columns", type: "two_column_row" },
  { command: "table", label: "Table", type: "table" },
  { command: "faq", label: "FAQ", type: "faq" },
  { command: "divider", label: "Divider", type: "divider" },
  { command: "embed", label: "Embed", type: "video_embed" },
  { command: "toc", label: "Table of contents", type: "table_of_contents" },
] as const;

export function newBlockId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `blk-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function defaultDocument(): BlogContentDocument {
  return {
    version: DOCUMENT_VERSION,
    settings: {
      content_width: "standard",
      show_table_of_contents: true,
      sticky_table_of_contents: false,
      reading_progress: true,
    },
    blocks: [createBlock("rich_text")],
  };
}

export function createBlock(type: string, partial?: Partial<BlogBlock>): BlogBlock {
  const base: BlogBlock = {
    id: newBlockId(),
    type,
    variant: "default",
    props: {},
    content: defaultContentForType(type),
    children: defaultChildrenForType(type),
  };
  return { ...base, ...partial, id: partial?.id ?? base.id };
}

function defaultContentForType(type: string): Record<string, unknown> {
  switch (type) {
    case "rich_text":
    case "legacy_rich_text":
      return { markdown: "", html: "" };
    case "heading":
      return { text: "Heading", level: 2 };
    case "image":
      return { url: "", alt: "", caption: "" };
    case "cta":
      return { label: "Learn more", href: "/events" };
    case "quote":
      return { text: "", attribution: "" };
    case "faq":
      return {
        items: [{ id: newBlockId(), question: "Question?", answer: "Answer." }],
      };
    case "table":
      return { headers: ["Column 1", "Column 2"], rows: [["", ""]] };
    case "list":
      return { items: ["Item one"], ordered: false };
    case "table_of_contents":
      return { include_h3: true };
    case "tip":
    case "warning":
    case "key_takeaway":
    case "important_note":
    case "author_note":
    case "pull_quote":
      return { text: "" };
    case "video_embed":
      return { provider: "youtube", embed_id: "" };
    case "two_column_row":
    case "three_column_row":
      return {};
    default:
      return {};
  }
}

function defaultChildrenForType(type: string): BlogBlock[] {
  if (type === "two_column_row") {
    return [createBlock("column"), createBlock("column")];
  }
  if (type === "three_column_row") {
    return [createBlock("column"), createBlock("column"), createBlock("column")];
  }
  if (type === "standard_section" || type === "full_width_section" || type === "narrow_section") {
    return [createBlock("rich_text")];
  }
  if (type === "column") {
    return [createBlock("rich_text")];
  }
  return [];
}

export function cloneBlockTree(block: BlogBlock): BlogBlock {
  const clone = (b: BlogBlock): BlogBlock => ({
    ...b,
    id: newBlockId(),
    props: { ...b.props },
    content: JSON.parse(JSON.stringify(b.content)),
    children: (b.children || []).map(clone),
  });
  return clone(block);
}

export function cloneDocument(doc: BlogContentDocument): BlogContentDocument {
  return {
    ...doc,
    settings: { ...doc.settings },
    blocks: doc.blocks.map(cloneBlockTree),
  };
}

export type OutlineItem = {
  blockId: string;
  text: string;
  level: number;
};

export function extractOutline(blocks: BlogBlock[]): OutlineItem[] {
  const items: OutlineItem[] = [];
  const walk = (list: BlogBlock[]) => {
    for (const b of list) {
      if (b.type === "heading") {
        const text = String(b.content.text || "");
        const level = Number(b.content.level || 2);
        if (text) items.push({ blockId: b.id, text, level });
      }
      if (b.children?.length) walk(b.children);
    }
  };
  walk(blocks);
  return items;
}

export function findBlockById(blocks: BlogBlock[], id: string): BlogBlock | null {
  for (const b of blocks) {
    if (b.id === id) return b;
    const found = findBlockById(b.children || [], id);
    if (found) return found;
  }
  return null;
}

export function findBlockPath(
  blocks: BlogBlock[],
  id: string,
  path: number[] = [],
): { block: BlogBlock; path: number[] } | null {
  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i];
    if (b.id === id) return { block: b, path: [...path, i] };
    const found = findBlockPath(b.children || [], id, [...path, i, -1].filter((x) => x >= 0));
    if (found) {
      // fix path for nested
      const nested = findBlockPathNested(b.children || [], id, [...path, i]);
      if (nested) return nested;
    }
  }
  return null;
}

function findBlockPathNested(
  blocks: BlogBlock[],
  id: string,
  parentPath: number[],
): { block: BlogBlock; path: number[] } | null {
  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i];
    if (b.id === id) return { block: b, path: [...parentPath, i] };
    const found = findBlockPathNested(b.children || [], id, [...parentPath, i]);
    if (found) return found;
  }
  return null;
}

export function updateBlockInTree(
  blocks: BlogBlock[],
  id: string,
  updater: (b: BlogBlock) => BlogBlock,
): BlogBlock[] {
  return blocks.map((b) => {
    if (b.id === id) return updater({ ...b });
    if (b.children?.length) {
      return { ...b, children: updateBlockInTree(b.children, id, updater) };
    }
    return b;
  });
}

export function removeBlockFromTree(blocks: BlogBlock[], id: string): BlogBlock[] {
  return blocks
    .filter((b) => b.id !== id)
    .map((b) => ({
      ...b,
      children: removeBlockFromTree(b.children || [], id),
    }));
}

export function insertBlockAtRoot(blocks: BlogBlock[], block: BlogBlock, index?: number): BlogBlock[] {
  const next = [...blocks];
  const idx = index ?? next.length;
  next.splice(idx, 0, block);
  return next;
}

export function flattenBlocksForStandard(blocks: BlogBlock[]): BlogBlock[] {
  /** Standard editor view: top-level + section children as sequential editable units. */
  const result: BlogBlock[] = [];
  const walk = (list: BlogBlock[], depth: number) => {
    for (const b of list) {
      const isLayoutContainer =
        b.type.includes("section") ||
        b.type.includes("row") ||
        b.type === "hero" ||
        b.type === "column";
      if (depth === 0 && isLayoutContainer && b.children.length > 0) {
        result.push({
          ...b,
          props: { ...b.props, _layoutBound: true },
        });
        for (const child of b.children) {
          if (child.type === "column") {
            walk(child.children, depth + 1);
          } else {
            result.push(child);
          }
        }
      } else if (!isLayoutContainer || b.type === "column") {
        if (b.type !== "column") result.push(b);
        if (b.children?.length && b.type !== "column") walk(b.children, depth + 1);
      } else {
        result.push(b);
      }
    }
  };
  walk(blocks, 0);
  return result.length ? result : blocks;
}

export function isBlockLocked(block: BlogBlock): boolean {
  return Boolean(block.props?.locked);
}

export function parseContentDocument(
  raw: Record<string, unknown> | null | undefined,
  bodyFallback?: string,
): BlogContentDocument {
  if (raw && typeof raw === "object" && Array.isArray(raw.blocks)) {
    return raw as unknown as BlogContentDocument;
  }
  if (bodyFallback?.trim()) {
    return {
      version: DOCUMENT_VERSION,
      settings: defaultDocument().settings,
      blocks: [
        {
          id: newBlockId(),
          type: "legacy_rich_text",
          variant: "default",
          props: {},
          content: { markdown: bodyFallback, html: "" },
          children: [],
        },
      ],
    };
  }
  return defaultDocument();
}

export function documentToMarkdown(doc: BlogContentDocument): string {
  const lines: string[] = [];
  const walk = (blocks: BlogBlock[]) => {
    for (const b of blocks) {
      if (b.type === "heading") {
        const level = Number(b.content.level || 2);
        lines.push(`${level === 3 ? "###" : "##"} ${b.content.text || ""}\n`);
      } else if (b.type === "rich_text" || b.type === "legacy_rich_text") {
        const md = String(b.content.markdown || "");
        if (md) lines.push(`${md}\n`);
      } else if (b.type === "cta") {
        lines.push(
          `::cta{label="${b.content.label || ""}"; href="${b.content.href || ""}"}\n`,
        );
      }
      if (b.children?.length) walk(b.children);
    }
  };
  walk(doc.blocks);
  return lines.join("\n").trim();
}

export function countBlocks(blocks: BlogBlock[]): number {
  let n = 0;
  const walk = (list: BlogBlock[]) => {
    for (const b of list) {
      n++;
      walk(b.children || []);
    }
  };
  walk(blocks);
  return n;
}
