import { describe, expect, it } from "vitest";

import {
  emailVerifyPath,
  postAuthPath,
} from "@/lib/auth/email-verify-path";

describe("emailVerifyPath", () => {
  it("defaults next to dashboard", () => {
    expect(emailVerifyPath()).toBe("/verify?next=%2Fdashboard");
    expect(emailVerifyPath(null)).toBe("/verify?next=%2Fdashboard");
  });

  it("preserves safe next paths", () => {
    expect(emailVerifyPath("/host")).toBe("/verify?next=%2Fhost");
  });

  it("does not nest verify paths", () => {
    expect(emailVerifyPath("/verify")).toBe("/verify");
  });
});

describe("postAuthPath", () => {
  it("sends unverified users to verify", () => {
    expect(postAuthPath({ is_verified: false }, "/dashboard")).toBe(
      "/verify?next=%2Fdashboard",
    );
  });

  it("sends verified users to next", () => {
    expect(postAuthPath({ is_verified: true }, "/host")).toBe("/host");
  });
});
