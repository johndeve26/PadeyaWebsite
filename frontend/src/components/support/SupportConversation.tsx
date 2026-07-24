"use client";

import { useMemo } from "react";

import {
  Card,
  EmptyState,
  SectionHeader,
  Timeline,
} from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import type { SupportCase } from "@/lib/types/support";

/**
 * Public + requester conversation view.
 * NEVER render internal_notes here.
 */
export function SupportConversation({
  ticket,
  filterInternalMessages = true,
}: {
  ticket: SupportCase;
  /** When true, hide staff-only message flags (safety for user views). */
  filterInternalMessages?: boolean;
}) {
  const timelineItems = useMemo(() => {
    const messages = filterInternalMessages
      ? ticket.messages.filter((m) => !m.is_internal)
      : ticket.messages;
    return [...messages]
      .sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      )
      .map((m) => ({
        id: m.id,
        title: m.author_name ?? "Participant",
        description: m.body,
        meta: (
          <span className="text-xs text-muted-foreground">
            {formatDateTime(m.created_at)}
          </span>
        ),
      }));
  }, [ticket.messages, filterInternalMessages]);

  const publicAttachments = (ticket.attachments ?? []).filter(
    (a) => !a.is_internal,
  );

  return (
    <div className="space-y-4">
      <Card className="space-y-4">
        <SectionHeader
          eyebrow="Conversation"
          title="Messages"
          description="Updates from you and Pàdéyá support."
        />
        {timelineItems.length > 0 ? (
          <Timeline items={timelineItems} />
        ) : (
          <EmptyState
            title="No messages yet"
            description="Replies will appear here once support responds."
          />
        )}
      </Card>

      {publicAttachments.length > 0 ? (
        <Card className="space-y-3">
          <SectionHeader eyebrow="Files" title="Attachments" />
          <ul className="space-y-2 text-sm">
            {publicAttachments.map((a) => (
              <li
                key={a.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-border px-3 py-2"
              >
                <span className="font-medium text-foreground">{a.filename}</span>
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(a.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
