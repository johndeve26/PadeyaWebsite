"use client";

import Link from "next/link";

import {
  Badge,
  Button,
  Media,
  StatusBadge,
} from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { formatAccessType } from "@/lib/vault-lock-copy";
import type { VaultStudioItem } from "@/lib/types/vault";

type Props = {
  item: VaultStudioItem;
  featured?: boolean;
  busy?: boolean;
  onArchive?: () => void;
  onUnpublish?: () => void;
  onPublish?: () => void;
  onRestore?: () => void;
};

export function VaultStudioItemCard({
  item,
  featured = false,
  busy = false,
  onArchive,
  onUnpublish,
  onPublish,
  onRestore,
}: Props) {
  const accessType = item.access?.access_type || "free";
  const earnings = Number(item.earnings || 0);

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)] transition-shadow duration-200 hover:shadow-[var(--shadow)]">
      <div className="relative aspect-[16/10] bg-surface-dark">
        {item.cover_url ? (
          <Media src={item.cover_url} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="padeya-hero-glow absolute inset-0" />
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/80 to-transparent px-3 pb-3 pt-10">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-subtle-foreground">
            {item.content_type.replace(/_/g, " ")}
          </p>
        </div>
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          <StatusBadge status={item.status} />
          <Badge tone="accent">{formatAccessType(accessType)}</Badge>
          {featured ? <Badge tone="dark">Legacy featured</Badge> : null}
          {item.is_expired ? <Badge tone="dark">Expired</Badge> : null}
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-4 sm:p-5">
        <div className="space-y-1">
          <h3 className="text-lg font-extrabold tracking-tight text-foreground">
            {item.title}
          </h3>
          {item.related_event ? (
            <p className="text-sm text-muted-foreground">
              Event · {item.related_event.title}
            </p>
          ) : item.related_event_id ? (
            <p className="text-sm text-muted-foreground">Linked to an event</p>
          ) : (
            <p className="text-sm text-muted-foreground">No related event</p>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 rounded-[var(--radius-md)] bg-muted/80 px-3 py-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
              Views
            </p>
            <p className="text-sm font-extrabold text-foreground">{item.view_count}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
              Unlocks
            </p>
            <p className="text-sm font-extrabold text-foreground">{item.unlock_count}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
              Earnings
            </p>
            <p className="text-sm font-extrabold text-foreground">
              {earnings > 0 ? formatNgn(earnings) : "—"}
            </p>
          </div>
        </div>

        <div className="mt-auto flex flex-wrap gap-2">
          <Link href={`/host/vault/${item.id}/edit`}>
            <Button size="sm">Edit</Button>
          </Link>
          <Link href={`/host/vault/${item.id}/preview`}>
            <Button size="sm" variant="secondary">
              Preview
            </Button>
          </Link>
          <Link href={`/host/vault/${item.id}`}>
            <Button size="sm" variant="ghost">
              Open
            </Button>
          </Link>
          {(item.status === "published" || item.status === "scheduled") &&
          onUnpublish ? (
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={onUnpublish}
            >
              Unpublish
            </Button>
          ) : null}
          {item.status === "draft" && onPublish ? (
            <Button size="sm" variant="secondary" disabled={busy} onClick={onPublish}>
              Publish
            </Button>
          ) : null}
          {item.status !== "archived" &&
          item.status !== "hidden_by_admin" &&
          onArchive ? (
            <Button
              size="sm"
              variant="ghost"
              className="text-danger"
              disabled={busy}
              onClick={onArchive}
            >
              Archive
            </Button>
          ) : null}
          {(item.status === "archived" || item.status === "expired") && onRestore ? (
            <Button size="sm" variant="secondary" disabled={busy} onClick={onRestore}>
              Restore draft
            </Button>
          ) : null}
          {item.status === "hidden_by_admin" ? (
            <p className="w-full text-xs text-danger">
              Hidden by admin — moderation restore required
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}
