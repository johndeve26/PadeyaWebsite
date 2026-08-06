import { describe, expect, it } from "vitest";

import { shouldHideAssistant } from "@/lib/assistant/checkout-guard";

describe("shouldHideAssistant", () => {
  it("hides event checkout paths", () => {
    expect(shouldHideAssistant("/events/abc/checkout")).toBe(true);
    expect(shouldHideAssistant("/events/abc/checkout/pay")).toBe(true);
    expect(shouldHideAssistant("/events/abc/checkout?step=1")).toBe(true);
  });

  it("hides merch checkout paths", () => {
    expect(shouldHideAssistant("/merch/xyz/checkout")).toBe(true);
    expect(shouldHideAssistant("/merch/xyz/checkout/confirm")).toBe(true);
  });

  it("hides top-level checkout", () => {
    expect(shouldHideAssistant("/checkout")).toBe(true);
    expect(shouldHideAssistant("/checkout/success")).toBe(true);
  });

  it("does not hide non-checkout routes", () => {
    expect(shouldHideAssistant("/")).toBe(false);
    expect(shouldHideAssistant("/events")).toBe(false);
    expect(shouldHideAssistant("/events/abc")).toBe(false);
    expect(shouldHideAssistant("/events/abc/details")).toBe(false);
    expect(shouldHideAssistant("/merch/xyz")).toBe(false);
    expect(shouldHideAssistant("/dashboard")).toBe(false);
    expect(shouldHideAssistant(null)).toBe(false);
    expect(shouldHideAssistant(undefined)).toBe(false);
  });
});
