"use client";

import Link from "next/link";

import type { StarredMessageItem } from "@/lib/types/messaging";

/** Inbox-side list of personally starred messages. Opens thread with `?m=` scroll target. */
export function StarredMessagesList({
  items,
  basePath,
}: {
  items: StarredMessageItem[];
  basePath: string;
}) {
  return (
    <>
      {items.map((row) => {
        const unavailable =
          row.message.status === "hidden" ||
          row.message.status === "deleted";
        const preview = unavailable
          ? row.message.body || "Message unavailable"
          : row.message.body?.trim() ||
            (row.message.attachments?.length ? "Attachment" : "Message");
        return (
          <Link
            key={`${row.thread_id}-${row.message.id}`}
            href={`${basePath}/${row.thread_id}?m=${encodeURIComponent(row.message.id)}`}
            className="block rounded-[var(--radius-md)] border border-transparent px-3 py-2 hover:bg-surface-muted"
          >
            <p className="text-sm font-bold text-foreground">
              {row.counterpart.display_name}
            </p>
            <p className="line-clamp-2 text-xs text-muted-foreground">
              {preview}
            </p>
          </Link>
        );
      })}
    </>
  );
}
