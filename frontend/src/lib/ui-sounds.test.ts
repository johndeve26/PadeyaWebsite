import { describe, expect, it } from "vitest";

import { scanOutcomeToSoundKind } from "./ui-sounds";

describe("scanOutcomeToSoundKind", () => {
  it("maps valid outcomes", () => {
    expect(scanOutcomeToSoundKind("success")).toBe("success");
    expect(scanOutcomeToSoundKind("valid")).toBe("success");
    expect(scanOutcomeToSoundKind("duplicate")).toBe("warning");
    expect(scanOutcomeToSoundKind("queued")).toBe("warning");
    expect(scanOutcomeToSoundKind("invalid")).toBe("error");
    expect(scanOutcomeToSoundKind("unknown")).toBe("info");
  });
});
