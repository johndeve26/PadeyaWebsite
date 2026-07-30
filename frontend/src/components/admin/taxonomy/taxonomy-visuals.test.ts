import { describe, expect, it } from "vitest";

import { IMAGE_CAPABLE_LOCATION_KINDS } from "@/components/admin/taxonomy/TaxonomyVisualsEditor";

describe("TaxonomyVisualsEditor constants", () => {
  it("allows visuals for city, state, and area locations only", () => {
    expect(IMAGE_CAPABLE_LOCATION_KINDS.has("city")).toBe(true);
    expect(IMAGE_CAPABLE_LOCATION_KINDS.has("state")).toBe(true);
    expect(IMAGE_CAPABLE_LOCATION_KINDS.has("area")).toBe(true);
    expect(IMAGE_CAPABLE_LOCATION_KINDS.has("country")).toBe(false);
    expect(IMAGE_CAPABLE_LOCATION_KINDS.has("tag")).toBe(false);
  });
});
