"use client";

import { useMemo, useState } from "react";

import {
  Card,
  Input,
  SectionHeader,
  Select,
  StatCard,
} from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { minorToMajor, previewFees } from "@/lib/fee-preview";
import type { HostFeeOverride, PlatformFeeSetting } from "@/lib/types/fees";
import { PAYER_COPY } from "@/lib/types/fees";

type HostOption = { id: string; label: string };

type Props = {
  settings: PlatformFeeSetting[];
  overrides: HostFeeOverride[];
  hosts?: HostOption[];
  defaultHostId?: string;
};

export function FeePreviewCalculator({
  settings,
  overrides,
  hosts = [],
  defaultHostId = "",
}: Props) {
  const [amount, setAmount] = useState("10000");
  const [category, setCategory] = useState<"ticket" | "merch" | "vault">(
    "ticket",
  );
  const [hostId, setHostId] = useState(defaultHostId);

  const preview = useMemo(() => {
    const major = Number(amount);
    return previewFees({
      baseAmountMajor: Number.isFinite(major) ? major : 0,
      category,
      settings,
      overrides,
      hostId: hostId.trim() || null,
    });
  }, [amount, category, settings, overrides, hostId]);

  return (
    <Card className="space-y-4 p-5">
      <SectionHeader
        title="Fee preview calculator"
        description="Sample how fees split for a given amount and host. Buyer-paid fees increase buyer total. Host-paid fees reduce host earnings. Platform-absorbed fees reduce platform margin."
      />
      <div className="grid gap-3 sm:grid-cols-3">
        <Input
          label="Sample amount (₦)"
          type="number"
          min={0}
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <Select
          label="Product"
          value={category}
          onChange={(e) =>
            setCategory(e.target.value as "ticket" | "merch" | "vault")
          }
        >
          <option value="ticket">Ticket</option>
          <option value="merch">Merch</option>
          <option value="vault">Vault</option>
        </Select>
        {hosts.length > 0 ? (
          <Select
            label="Host"
            value={hostId}
            onChange={(e) => setHostId(e.target.value)}
          >
            <option value="">Global rates only</option>
            {hosts.map((h) => (
              <option key={h.id} value={h.id}>
                {h.label}
              </option>
            ))}
          </Select>
        ) : (
          <Input
            label="Host ID (optional)"
            value={hostId}
            onChange={(e) => setHostId(e.target.value)}
            placeholder="UUID for override preview"
          />
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title={`${category} price`}
          value={formatNgn(minorToMajor(preview.base_amount_minor), {
            fractionDigits: 2,
          })}
        />
        <StatCard
          title="Buyer fees"
          value={formatNgn(minorToMajor(preview.buyer_fees_minor), {
            fractionDigits: 2,
          })}
        />
        <StatCard
          title="Buyer total"
          value={formatNgn(minorToMajor(preview.buyer_total_minor), {
            fractionDigits: 2,
          })}
        />
        <StatCard
          title="Host deductions"
          value={formatNgn(minorToMajor(preview.host_fees_minor), {
            fractionDigits: 2,
          })}
        />
        <StatCard
          title="Host net"
          value={formatNgn(minorToMajor(preview.host_net_minor), {
            fractionDigits: 2,
          })}
        />
        <StatCard
          title="Platform revenue"
          value={formatNgn(minorToMajor(preview.platform_revenue_minor), {
            fractionDigits: 2,
          })}
        />
      </div>

      {preview.lines.length > 0 ? (
        <ul className="divide-y divide-border rounded-lg border border-border text-sm">
          {preview.lines.map((line) => (
            <li
              key={`${line.fee_key}-${line.source}`}
              className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
            >
              <div>
                <p className="font-medium text-heading">{line.label}</p>
                <p className="text-xs text-muted-foreground">
                  {line.source === "host_override" ? "Host override" : "Global"}{" "}
                  · {line.payer} · {PAYER_COPY[line.payer] ?? ""}
                </p>
              </div>
              <p className="tabular-nums text-foreground">
                {formatNgn(minorToMajor(line.amount_minor), {
                  fractionDigits: 2,
                })}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          No active fees apply for this sample.
        </p>
      )}
    </Card>
  );
}
