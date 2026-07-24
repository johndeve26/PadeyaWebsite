import { describe, expect, it } from "vitest";

import { buildPathBreadcrumbs, labelForSegment } from "./breadcrumbs";

describe("buildPathBreadcrumbs", () => {
  it("shows Personal / Overview on /dashboard", () => {
    const { items } = buildPathBreadcrumbs("/dashboard", {
      homeLabel: "Personal",
      homeHref: "/dashboard",
    });
    expect(items).toEqual([
      { label: "Personal", href: "/dashboard" },
      { label: "Overview" },
    ]);
  });

  it("shows Personal / Workspaces on /dashboard/team", () => {
    const { items } = buildPathBreadcrumbs("/dashboard/team", {
      homeLabel: "Personal",
      homeHref: "/dashboard",
    });
    expect(items).toEqual([
      { label: "Personal", href: "/dashboard" },
      { label: "Workspaces" },
    ]);
  });

  it("shows Personal / Ambassadors on /dashboard/ambassador", () => {
    const { items } = buildPathBreadcrumbs("/dashboard/ambassador", {
      homeLabel: "Personal",
      homeHref: "/dashboard",
    });
    expect(items).toEqual([
      { label: "Personal", href: "/dashboard" },
      { label: "Ambassadors" },
    ]);
  });

  it("shows Host: name / Overview on /host", () => {
    const { items } = buildPathBreadcrumbs("/host", {
      homeLabel: "Host: DJ Maze",
      homeHref: "/host",
    });
    expect(items).toEqual([
      { label: "Host: DJ Maze", href: "/host" },
      { label: "Overview" },
    ]);
  });

  it("shows Host: name / Host Team on /host/team", () => {
    const { items } = buildPathBreadcrumbs("/host/team", {
      homeLabel: "Host: DJ Maze",
      homeHref: "/host",
    });
    expect(items).toEqual([
      { label: "Host: DJ Maze", href: "/host" },
      { label: "Host Team" },
    ]);
  });

  it("collapses role landing /host/desk to a single crumb", () => {
    const { items } = buildPathBreadcrumbs("/host/desk", {
      homeLabel: "Host: Maze",
      homeHref: "/host/desk",
    });
    expect(items).toEqual([{ label: "Host: Maze" }]);
  });

  it("keeps Host: name as root when deeper under /host", () => {
    const { items } = buildPathBreadcrumbs("/host/events", {
      homeLabel: "Host: Maze",
      homeHref: "/host",
    });
    expect(items[0]).toEqual({ label: "Host: Maze", href: "/host" });
    expect(items[1]).toEqual({ label: "Events" });
  });
});

describe("labelForSegment", () => {
  it("maps desk and dashboard segments for chrome consistency", () => {
    expect(labelForSegment("desk")).toBe("Tickets & Entry");
    expect(labelForSegment("dashboard")).toBe("Personal");
    expect(labelForSegment("notifications")).toBe("Alerts");
    expect(labelForSegment("ambassador")).toBe("Ambassadors");
  });

  it("uses Host-disambiguated labels under /host only", () => {
    expect(labelForSegment("merchandise", { workspaceRoot: "host" })).toBe(
      "Merch Studio",
    );
    expect(labelForSegment("messages", { workspaceRoot: "host" })).toBe(
      "Host Inbox",
    );
    expect(labelForSegment("ambassadors", { workspaceRoot: "host" })).toBe(
      "Ambassador Campaigns",
    );
    expect(labelForSegment("audience", { workspaceRoot: "host" })).toBe(
      "Audience CRM",
    );
    expect(labelForSegment("vault", { workspaceRoot: "host" })).toBe(
      "Vault Studio",
    );
    expect(labelForSegment("team", { workspaceRoot: "host" })).toBe(
      "Host Team",
    );
    expect(labelForSegment("settings", { workspaceRoot: "host" })).toBe(
      "Host Settings",
    );
    expect(labelForSegment("legacy", { workspaceRoot: "host" })).toBe(
      "Legacy Page",
    );
    // Personal dashboard keeps Personal-mode labels.
    expect(labelForSegment("merchandise")).toBe("Merchandise");
    expect(labelForSegment("messages")).toBe("Messages");
    expect(labelForSegment("vault")).toBe("Vault");
    expect(labelForSegment("team")).toBe("Workspaces");
  });
});

describe("buildPathBreadcrumbs host labels", () => {
  it("shows Merch Studio on host merchandise crumbs", () => {
    const { items } = buildPathBreadcrumbs("/host/merchandise", {
      homeLabel: "Host: Maze",
      homeHref: "/host",
    });
    expect(items[1]?.label).toBe("Merch Studio");
  });
});
