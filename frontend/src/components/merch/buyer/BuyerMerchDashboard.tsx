"use client";

import { useMemo, useState } from "react";

import { BuyerMerchEmptyState } from "@/components/merch/buyer/BuyerMerchEmptyState";
import { BuyerMerchPassCard } from "@/components/merch/buyer/BuyerMerchPassCard";
import { BuyerMerchSummaryCards } from "@/components/merch/buyer/BuyerMerchSummaryCards";
import { BuyerMerchTabs } from "@/components/merch/buyer/BuyerMerchTabs";
import { EligiblePostEventDrops } from "@/components/merch/buyer/EligiblePostEventDrops";
import { MerchPickupQrModal } from "@/components/merch/buyer/MerchPickupQrModal";
import { SectionHeader } from "@/components/ui";
import {
  filterMerchForTab,
  summarizeMerchWallet,
  type MerchWalletTab,
} from "@/lib/merch/buyer-merch-wallet";
import type { MerchCatalogProduct, MerchFulfillment } from "@/lib/types/merch";

function initialTab(rows: MerchFulfillment[]): MerchWalletTab {
  const s = summarizeMerchWallet(rows);
  if (s.ready > 0) return "ready";
  if (s.inProgress > 0) return "shipping";
  if (s.completed > 0) return "completed";
  if (s.cancelled > 0) return "cancelled";
  return "all";
}

function sectionCopy(tab: MerchWalletTab): {
  title: string;
  description: string;
} {
  if (tab === "ready") {
    return {
      title: "Ready for pickup",
      description: "Open your pickup QR at the merch stand.",
    };
  }
  if (tab === "shipping") {
    return {
      title: "Shipping / Delivery",
      description: "Orders being processed, shipped, or prepared for pickup.",
    };
  }
  if (tab === "completed") {
    return {
      title: "Picked up and delivered",
      description: "Completed merch — history only.",
    };
  }
  if (tab === "cancelled") {
    return {
      title: "Cancelled / Refunded",
      description: "These items are no longer available for pickup.",
    };
  }
  return {
    title: "All merch",
    description: "Ready pickup first, then in-progress and past orders.",
  };
}

function toneForTab(
  tab: MerchWalletTab,
): "active" | "completed" | "cancelled" {
  if (tab === "completed") return "completed";
  if (tab === "cancelled") return "cancelled";
  return "active";
}

export function BuyerMerchDashboard({
  rows,
  drops,
}: {
  rows: MerchFulfillment[];
  drops: MerchCatalogProduct[];
}) {
  const [tab, setTab] = useState<MerchWalletTab>(() => initialTab(rows));
  const [qrRow, setQrRow] = useState<MerchFulfillment | null>(null);
  const summary = useMemo(() => summarizeMerchWallet(rows), [rows]);

  const readyRows = useMemo(
    () => filterMerchForTab(rows, "ready"),
    [rows],
  );
  const shippingRows = useMemo(
    () => filterMerchForTab(rows, "shipping"),
    [rows],
  );
  const completedRows = useMemo(
    () => filterMerchForTab(rows, "completed"),
    [rows],
  );
  const cancelledRows = useMemo(
    () => filterMerchForTab(rows, "cancelled"),
    [rows],
  );

  const filtered =
    tab === "ready"
      ? readyRows
      : tab === "shipping"
        ? shippingRows
        : tab === "completed"
          ? completedRows
          : tab === "cancelled"
            ? cancelledRows
            : null;

  const empty =
    tab === "all"
      ? rows.length === 0
      : (filtered?.length ?? 0) === 0;

  const copy = sectionCopy(tab);

  // Default to most useful tab when ready is empty but others exist
  // (only on first meaningful load — keep simple: if ready=0 and shipping>0 stay on ready empty)

  return (
    <div className="w-full space-y-6">
      <BuyerMerchSummaryCards
        summary={summary}
        activeTab={tab}
        onSelect={setTab}
      />

      <EligiblePostEventDrops drops={drops} />

      <BuyerMerchTabs
        activeTab={tab}
        counts={{
          ready: summary.ready,
          shipping: summary.inProgress,
          completed: summary.completed,
          cancelled: summary.cancelled,
          all: summary.total,
        }}
        onChange={setTab}
      >
        {empty ? (
          <BuyerMerchEmptyState tab={tab} />
        ) : tab !== "all" ? (
          <div className="space-y-4">
            <SectionHeader
              title={copy.title}
              description={copy.description}
              className="pb-0"
            />
            <ul className="m-0 list-none space-y-4 p-0">
              {(filtered || []).map((row) => (
                <li key={`${row.id}-${row.order_item_id}`}>
                  <BuyerMerchPassCard
                    row={row}
                    tone={toneForTab(tab)}
                    onPickupQr={setQrRow}
                  />
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="space-y-8">
            {readyRows.length ? (
              <section className="space-y-3">
                <SectionHeader
                  title="Ready for pickup"
                  description="Open your pickup QR at the merch stand."
                  className="pb-0"
                />
                <ul className="m-0 list-none space-y-4 p-0">
                  {readyRows.map((row) => (
                    <li key={`${row.id}-${row.order_item_id}`}>
                      <BuyerMerchPassCard
                        row={row}
                        tone="active"
                        onPickupQr={setQrRow}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {shippingRows.length ? (
              <section className="space-y-3">
                <SectionHeader
                  title="Shipping / Delivery"
                  description="Orders being processed or shipped."
                  className="pb-0"
                />
                <ul className="m-0 list-none space-y-4 p-0">
                  {shippingRows.map((row) => (
                    <li key={`${row.id}-${row.order_item_id}`}>
                      <BuyerMerchPassCard
                        row={row}
                        tone="active"
                        onPickupQr={setQrRow}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {completedRows.length ? (
              <section className="space-y-3">
                <SectionHeader
                  title="Picked up and delivered"
                  description="Completed merch."
                  className="pb-0"
                />
                <ul className="m-0 list-none space-y-4 p-0">
                  {completedRows.map((row) => (
                    <li key={`${row.id}-${row.order_item_id}`}>
                      <BuyerMerchPassCard
                        row={row}
                        tone="completed"
                        onPickupQr={setQrRow}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {cancelledRows.length ? (
              <section className="space-y-3">
                <SectionHeader
                  title="Cancelled / Refunded"
                  description="No longer available for pickup."
                  className="pb-0"
                />
                <ul className="m-0 list-none space-y-4 p-0">
                  {cancelledRows.map((row) => (
                    <li key={`${row.id}-${row.order_item_id}`}>
                      <BuyerMerchPassCard
                        row={row}
                        tone="cancelled"
                        onPickupQr={setQrRow}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        )}
      </BuyerMerchTabs>

      {qrRow ? (
        <MerchPickupQrModal
          key={qrRow.order_item_id || qrRow.id}
          orderItemId={qrRow.order_item_id || qrRow.id}
          seed={qrRow}
          open
          onClose={() => setQrRow(null)}
        />
      ) : null}
    </div>
  );
}
