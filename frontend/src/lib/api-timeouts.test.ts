import { afterEach, describe, expect, it, vi } from "vitest";

import {
  API_TIMEOUT_MS,
  TimeoutError,
  createTimeoutSignal,
  isTimeoutError,
  timeoutMsFor,
  timeoutOrErrorMessage,
} from "@/lib/api-timeouts";

describe("api timeout policy", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("exposes central budgets", () => {
    expect(API_TIMEOUT_MS.public).toBe(10_000);
    expect(API_TIMEOUT_MS.chrome).toBe(5_000);
    expect(API_TIMEOUT_MS.long).toBe(60_000);
  });

  it("resolves named budgets and explicit overrides", () => {
    expect(timeoutMsFor("public")).toBe(10_000);
    expect(timeoutMsFor("chrome")).toBe(5_000);
    expect(timeoutMsFor(12_345)).toBe(12_345);
    expect(timeoutMsFor(undefined, 9_000)).toBe(9_000);
  });

  it("recognizes TimeoutError", () => {
    const err = new TimeoutError();
    expect(isTimeoutError(err)).toBe(true);
    expect(timeoutOrErrorMessage(err)).toMatch(/timed out/i);
  });

  it("aborts via timeout signal", async () => {
    vi.useFakeTimers();
    const signal = createTimeoutSignal(25);
    const wait = new Promise<void>((resolve) => {
      signal.addEventListener("abort", () => resolve(), { once: true });
    });
    vi.advanceTimersByTime(30);
    await wait;
    expect(signal.aborted).toBe(true);
  });
});
