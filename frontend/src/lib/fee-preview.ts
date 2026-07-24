/**
 * Client-side fee preview using integer minor units (mirrors backend rules).
 * Never use floating point for final money amounts.
 */

import type { HostFeeOverride, PlatformFeeSetting } from "@/lib/types/fees";

export type ResolvedFee = {
  fee_key: string;
  label: string;
  category: string;
  fee_type: string;
  percentage_value: number | null;
  fixed_value: number | null;
  payer: string;
  source: "global" | "host_override";
  currency: string;
};

export type FeePreviewLine = ResolvedFee & {
  amount_minor: number;
};

export type FeePreviewResult = {
  base_amount_minor: number;
  currency: string;
  lines: FeePreviewLine[];
  buyer_fees_minor: number;
  host_fees_minor: number;
  platform_absorbed_minor: number;
  buyer_total_minor: number;
  host_net_minor: number;
  platform_revenue_minor: number;
};

const TICKET_KEYS = new Set([
  "ticket_commission",
  "ticket_fixed_fee",
  "buyer_service_fee",
  "payment_processing_fee",
]);
const MERCH_KEYS = new Set([
  "merch_commission",
  "merch_fixed_fee",
  "buyer_service_fee",
  "payment_processing_fee",
]);
const VAULT_KEYS = new Set([
  "vault_commission",
  "vault_fixed_fee",
  "buyer_service_fee",
  "payment_processing_fee",
]);

export function majorToMinor(amountMajor: number): number {
  if (!Number.isFinite(amountMajor)) return 0;
  return Math.round(amountMajor * 100);
}

export function minorToMajor(amountMinor: number): number {
  return amountMinor / 100;
}

export function applyPercentage(baseMinor: number, percentage: number): number {
  if (!baseMinor || !percentage) return 0;
  // Half-up via integer math on 0.01% of a percent? Use Math.round on exact:
  // amount = base * pct / 100
  return Math.round((baseMinor * percentage) / 100);
}

function toNum(value: string | number | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function isEffective(
  from: string,
  to: string | null | undefined,
  at: Date,
): boolean {
  const start = new Date(from);
  if (Number.isNaN(start.getTime()) || start > at) return false;
  if (to) {
    const end = new Date(to);
    if (!Number.isNaN(end.getTime()) && end <= at) return false;
  }
  return true;
}

function activeGlobals(
  settings: PlatformFeeSetting[],
  at: Date,
): Map<string, PlatformFeeSetting> {
  const byKey = new Map<string, PlatformFeeSetting>();
  for (const row of settings) {
    if (!row.enabled) continue;
    if (!isEffective(row.effective_from, row.effective_to, at)) continue;
    const existing = byKey.get(row.fee_key);
    if (
      !existing ||
      new Date(row.effective_from) > new Date(existing.effective_from)
    ) {
      byKey.set(row.fee_key, row);
    }
  }
  return byKey;
}

function activeOverrides(
  overrides: HostFeeOverride[],
  hostId: string | null,
  at: Date,
): Map<string, HostFeeOverride> {
  const byKey = new Map<string, HostFeeOverride>();
  if (!hostId) return byKey;
  for (const row of overrides) {
    if (row.host_id !== hostId || !row.enabled) continue;
    if (!isEffective(row.effective_from, row.effective_to, at)) continue;
    const existing = byKey.get(row.fee_key);
    if (
      !existing ||
      new Date(row.effective_from) > new Date(existing.effective_from)
    ) {
      byKey.set(row.fee_key, row);
    }
  }
  return byKey;
}

export function resolveActiveFees(
  settings: PlatformFeeSetting[],
  overrides: HostFeeOverride[],
  hostId: string | null,
  at: Date = new Date(),
): ResolvedFee[] {
  const globals = activeGlobals(settings, at);
  const hostMap = activeOverrides(overrides, hostId, at);
  const keys = new Set([...globals.keys(), ...hostMap.keys()]);
  const resolved: ResolvedFee[] = [];

  for (const feeKey of keys) {
    const g = globals.get(feeKey);
    const o = hostMap.get(feeKey);
    if (o) {
      const pct = toNum(o.percentage_value) ?? toNum(g?.percentage_value);
      const fixed =
        o.fixed_value != null ? o.fixed_value : (g?.fixed_value ?? null);
      let feeType = "percentage";
      if (pct != null && fixed != null) feeType = "mixed";
      else if (fixed != null && pct == null) feeType = "fixed";
      resolved.push({
        fee_key: feeKey,
        label: g?.label ?? feeKey,
        category: g?.category ?? "general",
        fee_type: feeType,
        percentage_value: pct,
        fixed_value: fixed,
        payer: o.payer,
        source: "host_override",
        currency: g?.currency ?? "NGN",
      });
    } else if (g) {
      resolved.push({
        fee_key: g.fee_key,
        label: g.label,
        category: g.category,
        fee_type: g.fee_type,
        percentage_value: toNum(g.percentage_value),
        fixed_value: g.fixed_value,
        payer: g.payer,
        source: "global",
        currency: g.currency,
      });
    }
  }

  return resolved.sort((a, b) => a.fee_key.localeCompare(b.fee_key));
}

function keysForCategory(category: "ticket" | "merch" | "vault"): Set<string> {
  if (category === "merch") return MERCH_KEYS;
  if (category === "vault") return VAULT_KEYS;
  return TICKET_KEYS;
}

function computeLineAmount(
  baseMinor: number,
  feeType: string,
  percentage: number | null,
  fixed: number | null,
): number {
  let total = 0;
  if (feeType === "percentage" || feeType === "mixed") {
    total += applyPercentage(baseMinor, percentage ?? 0);
  }
  if (feeType === "fixed" || feeType === "mixed") {
    total += fixed ?? 0;
  }
  return total;
}

export function previewFees(input: {
  baseAmountMajor: number;
  category: "ticket" | "merch" | "vault";
  settings: PlatformFeeSetting[];
  overrides: HostFeeOverride[];
  hostId: string | null;
  currency?: string;
}): FeePreviewResult {
  const baseMinor = majorToMinor(input.baseAmountMajor);
  const allowed = keysForCategory(input.category);
  const resolved = resolveActiveFees(
    input.settings,
    input.overrides,
    input.hostId,
  ).filter((f) => allowed.has(f.fee_key));

  const lines: FeePreviewLine[] = [];
  let buyerFees = 0;
  let hostFees = 0;
  let platformAbsorbed = 0;

  for (const fee of resolved) {
    const amount = computeLineAmount(
      baseMinor,
      fee.fee_type,
      fee.percentage_value,
      fee.fixed_value,
    );
    if (amount === 0 && fee.percentage_value == null && !fee.fixed_value) {
      continue;
    }
    lines.push({ ...fee, amount_minor: amount });
    if (fee.payer === "buyer") buyerFees += amount;
    else if (fee.payer === "host") hostFees += amount;
    else platformAbsorbed += amount;
  }

  const hostNet = Math.max(0, baseMinor - hostFees);
  const platformRevenue = hostFees + buyerFees;

  return {
    base_amount_minor: baseMinor,
    currency: input.currency ?? "NGN",
    lines,
    buyer_fees_minor: buyerFees,
    host_fees_minor: hostFees,
    platform_absorbed_minor: platformAbsorbed,
    buyer_total_minor: baseMinor + buyerFees,
    host_net_minor: hostNet,
    platform_revenue_minor: platformRevenue,
  };
}

export function formatFeeRate(fee: {
  fee_type?: string;
  percentage_value: string | number | null;
  fixed_value: number | null;
  currency?: string;
}): string {
  const pct = toNum(fee.percentage_value);
  const fixedMajor =
    fee.fixed_value != null ? minorToMajor(fee.fixed_value) : null;
  const parts: string[] = [];
  const feeType = fee.fee_type || (pct != null && fixedMajor != null
    ? "mixed"
    : pct != null
      ? "percentage"
      : fixedMajor != null
        ? "fixed"
        : "");
  if (feeType === "percentage" || feeType === "mixed" || !fee.fee_type) {
    if (pct != null) parts.push(`${pct}%`);
  }
  if (feeType === "fixed" || feeType === "mixed" || !fee.fee_type) {
    if (fixedMajor != null) {
      parts.push(
        `₦${fixedMajor.toLocaleString("en-NG", {
          maximumFractionDigits: 2,
        })}`,
      );
    }
  }
  return parts.join(" + ") || "—";
}
