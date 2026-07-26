import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("events marketplace Link prefetch", () => {
  it("disables automatic prefetch on dense event card links", () => {
    const card = readFileSync(
      path.join(process.cwd(), "src/components/taxonomy/TaxonomyEventCard.tsx"),
      "utf8",
    );
    expect(card).toMatch(/prefetch=\{false\}/);
    expect(card.match(/prefetch=\{false\}/g)?.length ?? 0).toBeGreaterThanOrEqual(4);
  });

  it("disables prefetch on list/row and taxonomy discovery cards", () => {
    for (const rel of [
      "src/components/events/marketplace/EventResultRow.tsx",
      "src/components/events/marketplace/EventCompactRow.tsx",
      "src/components/taxonomy/CityCard.tsx",
      "src/components/taxonomy/CategoryCard.tsx",
      "src/components/taxonomy/TaxonomyHostCard.tsx",
    ]) {
      const src = readFileSync(path.join(process.cwd(), rel), "utf8");
      expect(src, rel).toMatch(/prefetch=\{false\}/);
    }
  });
});
