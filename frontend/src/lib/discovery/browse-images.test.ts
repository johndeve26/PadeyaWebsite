import { describe, expect, it } from "vitest";

import {
  categoryBrowseImage,
  categoryBrowseVisuals,
  cityBrowseImage,
  cityBrowseVisuals,
  taxonomyHeroAlt,
  taxonomyHeroFocal,
  taxonomyHeroImage,
} from "@/lib/discovery/browse-images";

describe("browse-images taxonomy visuals", () => {
  it("prefers admin URL over branded fallback for categories and cities", () => {
    const admin = "https://cdn.example.com/taxonomy/categories/x/primary/abc.png";
    expect(categoryBrowseImage("music", admin)).toBe(admin);
    expect(cityBrowseImage("lagos", admin)).toBe(admin);
  });

  it("falls back to deterministic SVG art when admin URL is absent", () => {
    expect(categoryBrowseImage("music")).toBe("/brand/browse/music.svg");
    expect(cityBrowseImage("lagos")).toBe("/brand/browse/city-lagos.svg");
  });

  it("resolves card visuals from taxonomy API fields", () => {
    const visuals = categoryBrowseVisuals("music", "Music", {
      primary_image_url: "https://cdn.example.com/music.png",
      primary_image_alt: "Live band",
      primary_image_focal_x: 0.25,
      primary_image_focal_y: 0.75,
    });
    expect(visuals.imageUrl).toBe("https://cdn.example.com/music.png");
    expect(visuals.imageAlt).toBe("Live band");
    expect(visuals.focalX).toBe(0.25);
    expect(visuals.focalY).toBe(0.75);
  });

  it("uses term name as alt fallback for city cards", () => {
    const visuals = cityBrowseVisuals("lagos", "Lagos", null);
    expect(visuals.imageAlt).toBe("Lagos");
    expect(visuals.focalX).toBe(0.5);
  });

  it("prefers hero image URL then primary for hub heroes", () => {
    expect(
      taxonomyHeroImage("music", "category", {
        heroUrl: "https://cdn.example.com/hero.png",
        primaryUrl: "https://cdn.example.com/primary.png",
      }),
    ).toBe("https://cdn.example.com/hero.png");
    expect(
      taxonomyHeroImage("music", "category", {
        primaryUrl: "https://cdn.example.com/primary.png",
      }),
    ).toBe("https://cdn.example.com/primary.png");
  });

  it("uses hero focal when hero image is set", () => {
    const focal = taxonomyHeroFocal({
      hero_image_url: "https://cdn.example.com/hero.png",
      hero_image_focal_x: 0.2,
      hero_image_focal_y: 0.8,
      primary_image_focal_x: 0.5,
      primary_image_focal_y: 0.5,
    });
    expect(focal).toEqual({ focalX: 0.2, focalY: 0.8 });
  });

  it("falls back to primary focal when hero image is unset", () => {
    const focal = taxonomyHeroFocal({
      primary_image_focal_x: 0.35,
      primary_image_focal_y: 0.65,
    });
    expect(focal).toEqual({ focalX: 0.35, focalY: 0.65 });
  });

  it("resolves hero alt from hero or primary fields", () => {
    expect(
      taxonomyHeroAlt(
        {
          hero_image_url: "https://cdn.example.com/hero.png",
          hero_image_alt: "Crowd at night",
        },
        "Nightlife",
      ),
    ).toBe("Crowd at night");
    expect(
      taxonomyHeroAlt({ primary_image_alt: "City skyline" }, "Lagos"),
    ).toBe("City skyline");
    expect(taxonomyHeroAlt(null, "Lagos")).toBe("Lagos");
  });

  it("uses hero image for cards when primary is unset", () => {
    const visuals = categoryBrowseVisuals("music", "Music", {
      hero_image_url: "https://cdn.example.com/hero.png",
      hero_image_alt: "Hero crowd",
      hero_image_focal_x: 0.2,
      hero_image_focal_y: 0.8,
    });
    expect(visuals.imageUrl).toBe("https://cdn.example.com/hero.png");
    expect(visuals.imageAlt).toBe("Hero crowd");
    expect(visuals.focalX).toBe(0.2);
  });
});
