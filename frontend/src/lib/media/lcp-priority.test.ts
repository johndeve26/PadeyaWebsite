import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("LCP priority is scoped to heroes", () => {
  it("homepage HeroSection preloads LCP with fetchPriority high", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/components/ui/HeroSection.tsx"),
      "utf8",
    );
    expect(src).toMatch(/\bpreload\b/);
    expect(src).toMatch(/fetchPriority=["']high["']/);
    expect(src).toMatch(/sizes="100vw"/);
    // Deprecated Next Image prop — must not appear as a JSX prop.
    expect(src).not.toMatch(/^\s*priority(?:=\{|=)/m);
  });

  it("event detail cover uses priority", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/components/events/EventPublicView.tsx"),
      "utf8",
    );
    expect(src).toMatch(/banner_url[\s\S]*?priority/);
    expect(src).toMatch(/sizes="hero"/);
  });

  it("marketplace event cards do not set priority", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/components/taxonomy/TaxonomyEventCard.tsx"),
      "utf8",
    );
    expect(src).toMatch(/sizes="eventCard"/);
    expect(src).not.toMatch(/priority/);
  });

  it("merch product hero uses priority; cards do not", () => {
    const detail = readFileSync(
      path.join(
        process.cwd(),
        "src/components/merch/marketplace/MerchProductDetailView.tsx",
      ),
      "utf8",
    );
    const card = readFileSync(
      path.join(process.cwd(), "src/components/merch/MerchProductCard.tsx"),
      "utf8",
    );
    expect(detail).toMatch(/priority/);
    expect(detail).toMatch(/sizes="merchHero"/);
    expect(card).toMatch(/sizes="merchCard"/);
    expect(card).not.toMatch(/priority/);
  });
});
