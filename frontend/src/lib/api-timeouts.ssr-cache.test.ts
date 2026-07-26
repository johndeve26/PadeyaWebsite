import { describe, expect, it } from "vitest";

import { withTimeoutRace } from "./api-timeouts";

describe("withTimeoutRace", () => {
  it("resolves the winning promise", async () => {
    const value = await withTimeoutRace(
      Promise.resolve("ok"),
      50,
      () => "timeout",
    );
    expect(value).toBe("ok");
  });

  it("falls back on timeout without aborting via signal", async () => {
    const value = await withTimeoutRace(
      new Promise<string>(() => {
        /* never settles */
      }),
      20,
      () => "timeout",
    );
    expect(value).toBe("timeout");
  });
});
