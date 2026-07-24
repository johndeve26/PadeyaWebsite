"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatNgn } from "@/lib/format";
import {
  fetchAdminMerchProduct,
  moderateMerchProduct,
} from "@/lib/merch-api";
import type { MerchAdminProduct, MerchModerateAction } from "@/lib/types/merch";

const REASON_REQUIRED = new Set<MerchModerateAction>([
  "hide",
  "archive",
  "restore",
]);

export default function AdminMerchandiseDetailPage() {
  const params = useParams<{ id: string }>();
  const [item, setItem] = useState<MerchAdminProduct | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const row = await fetchAdminMerchProduct(params.id);
    setItem(row);
  }, [params.id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoading(true);
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Product not found");
          setItem(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onModerate(action: MerchModerateAction) {
    if (!item) return;
    const itemNote = reason.trim();
    if (REASON_REQUIRED.has(action) && !itemNote) {
      setError("Moderation reason is required for hide, archive, and restore");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const updated = await moderateMerchProduct(
        item.id,
        action,
        itemNote || undefined,
      );
      setItem(updated);
      setReason("");
      const labels: Record<MerchModerateAction, string> = {
        flag: "flagged",
        clear: "cleared",
        hide: "hidden",
        remove: "archived",
        archive: "archived",
        restore: "restored",
      };
      setNote(`Merchandise ${labels[action]}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Moderation failed");
    } finally {
      setBusy(false);
    }
  }

  const mod = item?.moderation_status ?? "clear";
  const canHide = item && mod !== "hidden" && mod !== "removed";
  const canRestore = item && (mod === "hidden" || mod === "removed");
  const canArchive =
    item && item.status !== "archived" && mod !== "removed";

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title={item?.name ?? "Merch product"}
      description="Product detail for moderation. Hidden listings are not public and not purchasable."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/merchandise">
            <Button variant="secondary">All products</Button>
          </Link>
          <Link href="/admin/merchandise/reports">
            <Button variant="ghost">Reports</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Updated">
          {note}
        </Alert>
      ) : null}

      {loading ? <SkeletonLoader lines={6} /> : null}

      {!loading && !item ? (
        <EmptyState
          title="Product not found"
          description="This merch listing may have been removed from the admin index."
          action={
            <Link href="/admin/merchandise">
              <Button variant="secondary">Back to merchandise</Button>
            </Link>
          }
        />
      ) : null}

      {!loading && item ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-[160px_1fr]">
            <div className="overflow-hidden rounded-[var(--radius-md)] bg-surface-muted">
              {item.cover_image_url || item.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={item.cover_image_url || item.image_url || ""}
                  alt=""
                  className="aspect-square w-full object-cover"
                />
              ) : (
                <div className="flex aspect-square items-center justify-center text-sm font-bold text-muted-foreground">
                  No image
                </div>
              )}
            </div>
            <div className="space-y-3">
              <div className="flex flex-wrap gap-1.5">
                <StatusBadge status={item.status} />
                <StatusBadge status={mod} />
              </div>
              <p className="text-2xl font-extrabold text-foreground">
                {formatNgn(Number(item.base_price))}
              </p>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">Host</dt>
                  <dd className="font-medium text-foreground">
                    {item.host_name ?? "—"} ({item.host_status ?? "—"})
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Event</dt>
                  <dd className="font-medium text-foreground">
                    {item.event_title ?? "—"} ({item.event_status ?? "—"})
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Sales</dt>
                  <dd className="font-medium text-foreground">
                    {item.sold_count ?? 0}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Reports</dt>
                  <dd className="font-medium text-foreground">
                    {item.report_count ?? 0} total
                    {(item.open_report_count ?? 0) > 0
                      ? ` · ${item.open_report_count} open`
                      : ""}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Created</dt>
                  <dd className="font-medium text-foreground">
                    {formatDate(item.created_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Updated</dt>
                  <dd className="font-medium text-foreground">
                    {formatDateTime(item.updated_at)}
                  </dd>
                </div>
              </dl>
              {item.moderation_note ? (
                <Alert tone="warning" title="Moderation reason">
                  {item.moderation_note}
                </Alert>
              ) : null}
              {item.description || item.short_description ? (
                <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                  {item.description || item.short_description}
                </p>
              ) : null}
            </div>
          </div>

          <div className="space-y-3">
            <Textarea
              label="Moderation reason"
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Required for hide / archive / restore"
            />
            <div className="flex flex-wrap gap-2">
              {canHide ? (
                <ConfirmAction
                  label="Hide"
                  title="Hide this listing?"
                  description="Hidden products leave the public catalog and cannot be purchased. The host will see the hidden status and reason."
                  confirmLabel="Hide listing"
                  tone="danger"
                  disabled={busy}
                  busy={busy}
                  onConfirm={() => onModerate("hide")}
                />
              ) : null}
              {canRestore ? (
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void onModerate("restore")}
                >
                  Restore
                </Button>
              ) : null}
              {canArchive ? (
                <ConfirmAction
                  label="Archive"
                  title="Archive this listing?"
                  description="Archives the product (not public, not purchasable)."
                  confirmLabel="Archive"
                  tone="danger"
                  disabled={busy}
                  busy={busy}
                  onConfirm={() => onModerate("archive")}
                />
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </DashboardShell>
  );
}
