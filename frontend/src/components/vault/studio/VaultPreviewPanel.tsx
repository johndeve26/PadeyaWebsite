"use client";

import Link from "next/link";

import { Badge, Button, Card, Media } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import type { VaultItem } from "@/lib/types/vault";

export function VaultPreviewPanel({
  item,
  mode = "fan",
  surfaceLabel,
}: {
  item: VaultItem;
  mode?: "fan" | "owner";
  /** Optional override for the panel header label */
  surfaceLabel?: string;
}) {
  const locked = mode === "fan" ? item.locked || !item.has_access : false;
  const previewMedia = (item.media || []).filter((m) => m.is_preview && m.url);
  const unlockedMedia = (item.media || []).filter((m) => m.url && !m.locked);

  return (
    <div className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card dark:bg-surface-elevated">
      <div className="border-b border-border bg-muted px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
        {surfaceLabel ||
          (mode === "fan"
            ? "Fan preview · locked view"
            : "Owner view · full access")}
      </div>
      <div className="space-y-5 p-5">
        <div className="relative aspect-[16/10] overflow-hidden rounded-[var(--radius-lg)] bg-ink">
          {item.cover_url ? (
            <Media src={item.cover_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="padeya-hero-glow absolute inset-0" />
          )}
          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
            <Badge tone="accent">Vault</Badge>
            {locked ? <Badge tone="dark">Locked</Badge> : <Badge tone="dark">Unlocked</Badge>}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            {item.content_type.replace(/_/g, " ")}
          </p>
          <h3 className="text-2xl font-extrabold tracking-tight text-foreground">
            {item.title}
          </h3>
          {item.preview_text ? (
            <p className="text-base leading-relaxed text-muted-foreground">{item.preview_text}</p>
          ) : null}
          {item.description ? (
            <p className="text-sm leading-relaxed text-muted-foreground">{item.description}</p>
          ) : null}
        </div>

        <Card className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Access
          </p>
          <p className="text-sm font-semibold capitalize text-foreground">
            {(item.access?.access_type || "free").replace(/_/g, " ")}
          </p>
          {Number(item.price) > 0 ? (
            <p className="text-sm text-muted-foreground">
              {formatNgn(Number(item.price))} · {item.currency}
            </p>
          ) : null}
          {locked ? (
            <p className="text-sm text-muted-foreground">
              Full body and private media stay hidden until access rules are met.
            </p>
          ) : null}
        </Card>

        {locked ? (
          <div className="space-y-3">
            <p className="text-sm font-bold text-foreground">Public teaser media</p>
            {previewMedia.length === 0 ? (
              <p className="text-sm text-muted-foreground">No public preview media.</p>
            ) : (
              <ul className="space-y-2 text-sm text-muted-foreground">
                {previewMedia.map((m) => (
                  <li key={m.id || m.url}>
                    {m.label || m.media_type}: {m.url}
                  </li>
                ))}
              </ul>
            )}
            <div className="rounded-[var(--radius-md)] border border-dashed border-border bg-muted/60 px-4 py-6 text-center text-sm text-muted-foreground">
              Locked content placeholder — body and private files are not shown here.
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {item.body ? (
              <p className="whitespace-pre-wrap text-base leading-relaxed text-muted-foreground">
                {item.body}
              </p>
            ) : null}
            {item.file_url ? (
              <p className="text-sm text-muted-foreground">File: {item.file_url}</p>
            ) : null}
            {item.external_url ? (
              <p className="text-sm text-muted-foreground">External: {item.external_url}</p>
            ) : null}
            {unlockedMedia.length > 0 ? (
              <ul className="space-y-2 text-sm text-muted-foreground">
                {unlockedMedia.map((m) => (
                  <li key={m.id || m.url}>
                    {m.label || m.media_type}: {m.url}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        )}

        {item.host_username ? (
          <Link href={`/@${item.host_username}/vault/${item.slug}`}>
            <Button variant="secondary" size="sm">
              Open public page
            </Button>
          </Link>
        ) : null}
      </div>
    </div>
  );
}
