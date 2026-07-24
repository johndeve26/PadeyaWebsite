import { describe, expect, it } from "vitest";

import { applyPercentage, majorToMinor, previewFees } from "./fee-preview";
import type { HostFeeOverride, PlatformFeeSetting } from "./types/fees";

function setting(
  partial: Partial<PlatformFeeSetting> &
    Pick<PlatformFeeSetting, "fee_key" | "label" | "category" | "fee_type" | "payer">,
): PlatformFeeSetting {
  return {
    id: partial.id ?? "s1",
    percentage_value: partial.percentage_value ?? null,
    fixed_value: partial.fixed_value ?? null,
    currency: "NGN",
    enabled: partial.enabled ?? true,
    applies_to: "all",
    notes: null,
    effective_from: partial.effective_from ?? "2020-01-01T00:00:00Z",
    effective_to: partial.effective_to ?? null,
    created_by_admin_id: null,
    updated_by_admin_id: null,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
    ...partial,
  };
}

describe("fee preview calculator", () => {
  it("applies global ticket percentage and buyer service fee", () => {
    const settings = [
      setting({
        fee_key: "ticket_commission",
        label: "Ticket commission",
        category: "ticket",
        fee_type: "percentage",
        percentage_value: "5",
        payer: "host",
      }),
      setting({
        id: "s2",
        fee_key: "buyer_service_fee",
        label: "Buyer service fee",
        category: "general",
        fee_type: "mixed",
        percentage_value: "2",
        fixed_value: 100_00,
        payer: "buyer",
      }),
    ];

    const result = previewFees({
      baseAmountMajor: 10_000,
      category: "ticket",
      settings,
      overrides: [],
      hostId: null,
    });

    expect(result.base_amount_minor).toBe(1_000_000);
    expect(result.host_fees_minor).toBe(50_000);
    expect(result.buyer_fees_minor).toBe(20_000 + 10_000);
    expect(result.buyer_total_minor).toBe(1_030_000);
    expect(result.host_net_minor).toBe(950_000);
    expect(result.platform_revenue_minor).toBe(80_000);
  });

  it("lets host override beat global commission", () => {
    const settings = [
      setting({
        fee_key: "ticket_commission",
        label: "Ticket commission",
        category: "ticket",
        fee_type: "percentage",
        percentage_value: "5",
        payer: "host",
      }),
    ];
    const overrides: HostFeeOverride[] = [
      {
        id: "o1",
        host_id: "host-a",
        fee_key: "ticket_commission",
        percentage_value: "3",
        fixed_value: null,
        payer: "host",
        enabled: true,
        effective_from: "2020-01-01T00:00:00Z",
        effective_to: null,
        reason: "Preferred partner",
        created_by_admin_id: null,
        updated_by_admin_id: null,
        created_at: "2020-01-01T00:00:00Z",
        updated_at: "2020-01-01T00:00:00Z",
      },
    ];

    const result = previewFees({
      baseAmountMajor: 10_000,
      category: "ticket",
      settings,
      overrides,
      hostId: "host-a",
    });

    expect(result.host_fees_minor).toBe(30_000);
    expect(result.lines[0]?.source).toBe("host_override");
  });

  it("avoids float money errors", () => {
    expect(majorToMinor(0.1 + 0.2)).toBe(30);
    expect(applyPercentage(999_99, 0.1)).toBe(100);
  });
});
