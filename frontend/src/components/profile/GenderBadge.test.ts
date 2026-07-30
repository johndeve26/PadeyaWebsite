import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GenderBadge } from "@/components/profile/GenderBadge";
import { GenderFields } from "@/components/profile/GenderFields";
import {
  DEFAULT_GENDER_VISIBILITY,
  GENDER_VISIBILITY_HINTS,
  resolveGenderBadge,
} from "@/lib/gender";

describe("resolveGenderBadge", () => {
  it("returns M/F for male and female values", () => {
    expect(resolveGenderBadge("male")).toEqual({ short: "M", label: "Male" });
    expect(resolveGenderBadge("female")).toEqual({
      short: "F",
      label: "Female",
    });
  });

  it("hides prefer_not_to_say, null, and invisible payloads", () => {
    expect(resolveGenderBadge(null)).toBeNull();
    expect(
      resolveGenderBadge({
        gender: "prefer_not_to_say",
        gender_short: null,
        gender_label: "Prefer not to say",
        gender_visible: true,
      }),
    ).toBeNull();
    expect(
      resolveGenderBadge({
        gender: "male",
        gender_short: "M",
        gender_label: "Male",
        gender_visible: false,
      }),
    ).toBeNull();
  });
});

describe("GenderBadge", () => {
  it("renders compact M with screen-reader Male", () => {
    const html = renderToStaticMarkup(
      createElement(GenderBadge, { value: "male" }),
    );
    expect(html).toContain(">M<");
    expect(html).toContain("Male");
    expect(html).toContain("bg-ink");
    expect(html).toContain("text-primary");
    expect(html).not.toContain("pink");
    expect(html).not.toContain("blue");
  });

  it("uses onDark surface for ink passport bands", () => {
    const html = renderToStaticMarkup(
      createElement(GenderBadge, { value: "female", surface: "onDark" }),
    );
    expect(html).toContain(">F<");
    expect(html).toContain("bg-primary");
    expect(html).toContain("text-ink");
  });

  it("renders F for female display payload when visible", () => {
    const html = renderToStaticMarkup(
      createElement(GenderBadge, {
        value: {
          gender: "female",
          gender_short: "F",
          gender_label: "Female",
          gender_visible: true,
        },
      }),
    );
    expect(html).toContain(">F<");
    expect(html).toContain("Female");
  });

  it("renders nothing for prefer_not_to_say", () => {
    const html = renderToStaticMarkup(
      createElement(GenderBadge, {
        value: {
          gender: "prefer_not_to_say",
          gender_short: null,
          gender_label: "Prefer not to say",
          gender_visible: true,
        },
      }),
    );
    expect(html).toBe("");
  });
});

describe("GenderFields", () => {
  it("starts with no gender selected (signup has no default)", () => {
    const html = renderToStaticMarkup(
      createElement(GenderFields, {
        gender: null,
        onGenderChange: () => undefined,
        showVisibility: false,
        required: true,
      }),
    );
    expect(html).not.toMatch(/checked(=|"|\{)/);
    expect(html).toContain('value="male"');
    expect(html).toContain('value="female"');
    expect(html).toContain('value="prefer_not_to_say"');
  });

  it("marks the chosen gender and includes default public visibility hint", () => {
    const html = renderToStaticMarkup(
      createElement(GenderFields, {
        gender: "female",
        onGenderChange: () => undefined,
        genderVisibility: DEFAULT_GENDER_VISIBILITY,
        onVisibilityChange: () => undefined,
        showVisibility: true,
      }),
    );
    expect(html).toContain("Female");
    expect(html).toContain(GENDER_VISIBILITY_HINTS.public);
    expect(html).toContain("Everyone");
  });
});
