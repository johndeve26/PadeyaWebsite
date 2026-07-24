"use client";

import Link from "next/link";

import { Badge, Button, Card, Media } from "@/components/ui";
import {
  trackVaultDownloadClick,
  trackVaultMediaOpen,
} from "@/lib/analytics";
import type { VaultItem } from "@/lib/types/vault";

type Props = {
  item: VaultItem;
  hostId?: string | null;
  sourcePage?: string;
};

export function VaultItemUnlockedContent({
  item,
  hostId = null,
  sourcePage = "vault_item",
}: Props) {
  const media = (item.media || []).filter((m) => m.url);
  const resolvedHostId = hostId || item.host_id;

  function baseMeta(mediaId?: string | null) {
    return {
      hostId: resolvedHostId,
      vaultItemId: item.id,
      accessType: item.access?.access_type ?? null,
      relatedEventId: item.related_event?.id ?? item.related_event_id ?? null,
      lockedState: false as const,
      sourcePage,
      mediaId: mediaId ?? null,
    };
  }

  function onMediaOpen(mediaId?: string | null) {
    if (!resolvedHostId) return;
    trackVaultMediaOpen(baseMeta(mediaId));
  }

  function onDownloadClick(mediaId?: string | null) {
    if (!resolvedHostId) return;
    trackVaultDownloadClick(baseMeta(mediaId));
  }

  return (
    <Card className="space-y-6 shadow-[var(--shadow)]">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="accent">Unlocked</Badge>
        <Badge tone="dark">{(item.content_type || "drop").replace(/_/g, " ")}</Badge>
      </div>

      {item.body ? (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Content
          </p>
          <p className="whitespace-pre-wrap text-base leading-relaxed text-foreground sm:text-lg">
            {item.body}
          </p>
        </div>
      ) : null}

      {item.file_url ? (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Download
          </p>
          <a
            href={item.file_url}
            target="_blank"
            rel="noreferrer"
            onClick={() => onDownloadClick(null)}
          >
            <Button size="lg">Download file</Button>
          </a>
        </div>
      ) : null}

      {item.external_url ? (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            External link
          </p>
          <a
            href={item.external_url}
            target="_blank"
            rel="noreferrer"
            onClick={() => onMediaOpen(null)}
          >
            <Button size="lg" variant="secondary">
              Open link
            </Button>
          </a>
        </div>
      ) : null}

      {media.length > 0 ? (
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Media
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {media.map((m) =>
              m.media_type === "image" && m.url ? (
                <a
                  key={m.id}
                  href={m.url}
                  target="_blank"
                  rel="noreferrer"
                  className="relative block aspect-[16/10] overflow-hidden rounded-[var(--radius-md)] bg-surface-dark"
                  onClick={() => onMediaOpen(m.id)}
                >
                  <Media
                    src={m.url}
                    alt={m.label || ""}
                    className="h-full w-full object-cover"
                  />
                </a>
              ) : (
                <a
                  key={m.id}
                  className="flex items-center rounded-[var(--radius-md)] border border-border px-4 py-3 text-sm font-semibold text-foreground underline-offset-2 hover:bg-surface-muted hover:underline"
                  href={m.url!}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => {
                    if (m.media_type === "file" || m.media_type === "download") {
                      onDownloadClick(m.id);
                    } else {
                      onMediaOpen(m.id);
                    }
                  }}
                >
                  {m.label || m.media_type}
                </a>
              ),
            )}
          </div>
        </div>
      ) : null}

      {!item.body && !item.file_url && !item.external_url && media.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          This drop is unlocked. No additional body content was published.
        </p>
      ) : null}

      {item.related_event || item.related_memory ? (
        <div className="space-y-4 border-t border-border pt-4">
          {item.related_event ? (
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Related event
              </p>
              <Link
                href={item.related_event.href}
                className="mt-2 inline-flex text-base font-extrabold text-foreground underline-offset-2 hover:underline"
              >
                {item.related_event.title}
              </Link>
            </div>
          ) : null}
          {item.related_memory ? (
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Related memory
              </p>
              <Link
                href={item.related_memory.href}
                className="mt-2 inline-flex text-base font-extrabold text-foreground underline-offset-2 hover:underline"
              >
                {item.related_memory.event_title}
              </Link>
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
