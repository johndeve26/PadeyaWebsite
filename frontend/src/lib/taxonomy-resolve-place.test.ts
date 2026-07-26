import { describe, expect, it, vi } from "vitest";

import type { TaxonomyLocation } from "@/lib/taxonomy-api";
import {
  matchTaxonomyFromPlaceHints,
  publicLabelFromResolvedPlace,
} from "@/lib/taxonomy-resolve-place";

function loc(
  partial: Pick<TaxonomyLocation, "id" | "kind" | "name" | "slug"> & {
    parent_id?: string | null;
    country_code?: string | null;
    state_code?: string | null;
  },
): TaxonomyLocation {
  return {
    parent_id: partial.parent_id ?? null,
    is_active: true,
    country_code: partial.country_code ?? null,
    state_code: partial.state_code ?? null,
    ...partial,
  };
}

const nigeria = loc({
  id: "c-ng",
  kind: "country",
  name: "Nigeria",
  slug: "nigeria",
  country_code: "NG",
});
const lagosState = loc({
  id: "s-la",
  kind: "state",
  name: "Lagos",
  slug: "lagos",
  parent_id: "c-ng",
  state_code: "LA",
});
const lagosCity = loc({
  id: "ci-la",
  kind: "city",
  name: "Lagos",
  slug: "lagos",
  parent_id: "s-la",
});
const ikeja = loc({
  id: "a-ik",
  kind: "area",
  name: "Ikeja",
  slug: "ikeja",
  parent_id: "ci-la",
});
const lekki = loc({
  id: "a-lk",
  kind: "area",
  name: "Lekki",
  slug: "lekki",
  parent_id: "ci-la",
});
const lekkiPhase1 = loc({
  id: "a-lk1",
  kind: "area",
  name: "Lekki Phase 1",
  slug: "lekki-phase-1",
  parent_id: "ci-la",
});

const lookup = {
  countries: [nigeria],
  statesFor: async () => [lagosState],
  citiesFor: async () => [lagosCity],
  areasFor: async () => [ikeja, lekki, lekkiPhase1],
};

describe("matchTaxonomyFromPlaceHints", () => {
  it("resolves deepest area leaf when all hints match", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "Nigeria",
        stateHint: "Lagos",
        cityHint: "Lagos",
        areaHint: "Ikeja",
      },
      lookup,
    );
    expect(resolved?.locationId).toBe("a-ik");
    expect(resolved?.area).toBe("Ikeja");
    expect(resolved?.city).toBe("Lagos");
    expect(resolved?.leaf.id).toBe("a-ik");
  });

  it("falls back to city when area is missing from taxonomy", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "Nigeria",
        stateHint: "Lagos",
        cityHint: "Lagos",
        areaHint: "Unknown Neighbourhood XYZ",
      },
      lookup,
    );
    expect(resolved?.locationId).toBe("ci-la");
    expect(resolved?.area).toBe("");
    expect(resolved?.city).toBe("Lagos");
    expect(resolved?.leaf.kind).toBe("city");
  });

  it("returns null when country cannot be matched", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "Atlantis",
        stateHint: "Lagos",
        cityHint: "Lagos",
      },
      lookup,
    );
    expect(resolved).toBeNull();
  });

  it("matches by slug-ish name", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "nigeria",
        stateHint: "lagos",
        cityHint: "lagos",
        areaHint: "ikeja",
      },
      lookup,
    );
    expect(resolved?.locationId).toBe("a-ik");
  });

  it("strips State suffix and uses state-named city when locality is an LGA", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "Nigeria",
        stateHint: "Lagos State",
        cityHint: "Eti-Osa",
        areaHint: "Lekki Phase 1",
      },
      lookup,
    );
    expect(resolved?.state).toBe("Lagos");
    expect(resolved?.city).toBe("Lagos");
    expect(resolved?.area).toBe("Lekki Phase 1");
    expect(resolved?.locationId).toBe("a-lk1");
  });

  it("matches country by ISO code alias", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "NG",
        stateHint: "Lagos",
        cityHint: "Lagos",
        areaHint: "Lekki",
      },
      lookup,
    );
    expect(resolved?.country).toBe("Nigeria");
    expect(resolved?.area).toBe("Lekki");
  });

  it("soft-matches longer area names contained in the hint", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "Nigeria",
        stateHint: "Lagos",
        cityHint: "Lagos",
        areaHint: "Near Lekki Phase 1 waterfront",
      },
      lookup,
    );
    expect(resolved?.area).toBe("Lekki Phase 1");
  });
});

describe("publicLabelFromResolvedPlace", () => {
  it("prefers area, city for discovery label", async () => {
    const resolved = await matchTaxonomyFromPlaceHints(
      {
        countryHint: "Nigeria",
        stateHint: "Lagos",
        cityHint: "Lagos",
        areaHint: "Ikeja",
      },
      lookup,
    );
    expect(resolved).not.toBeNull();
    expect(publicLabelFromResolvedPlace(resolved!)).toBe("Ikeja, Lagos");
  });
});

describe("ensureTaxonomyFromPlaceHints", () => {
  it("creates missing area under matched city", async () => {
    vi.resetModules();
    vi.doMock("@/lib/taxonomy-api", async () => {
      const actual =
        await vi.importActual<typeof import("@/lib/taxonomy-api")>(
          "@/lib/taxonomy-api",
        );
      const areas = [ikeja, lekki, lekkiPhase1];
      return {
        ...actual,
        fetchTaxonomyLocations: vi.fn(
          async (opts?: { kind?: string; parentId?: string }) => {
            if (opts?.kind === "country") return [nigeria];
            if (opts?.kind === "state") return [lagosState];
            if (opts?.kind === "city") return [lagosCity];
            if (opts?.kind === "area") return [...areas];
            return [nigeria, lagosState, lagosCity, ...areas];
          },
        ),
        suggestTaxonomyArea: vi.fn(async ({ name }: { name: string }) => {
          const created = loc({
            id: "a-new",
            kind: "area",
            name,
            slug: name.toLowerCase().replace(/\s+/g, "-"),
            parent_id: "ci-la",
          });
          areas.push(created);
          return created;
        }),
        suggestTaxonomyCity: vi.fn(),
      };
    });

    const { ensureTaxonomyFromPlaceHints } = await import(
      "@/lib/taxonomy-resolve-place"
    );
    const resolved = await ensureTaxonomyFromPlaceHints({
      countryHint: "Nigeria",
      stateHint: "Lagos",
      cityHint: "Lagos",
      areaHint: "Brand New Estate",
    });
    expect(resolved?.area).toBe("Brand New Estate");
    expect(resolved?.created?.area).toBe(true);
    expect(resolved?.locationId).toBe("a-new");
  });
});
