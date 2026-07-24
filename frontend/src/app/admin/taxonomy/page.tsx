"use client";

import Link from "next/link";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, WorkspaceNavGrid } from "@/components/ui";
import type { WorkspaceNavItem } from "@/components/ui";

const LINKS: WorkspaceNavItem[] = [
  {
    href: "/admin/taxonomy/categories",
    title: "Categories",
    description: "Primary event categories and SEO.",
  },
  {
    href: "/admin/taxonomy/tags",
    title: "Tags",
    description: "Discoverable tags for events and hosts.",
  },
  {
    href: "/admin/taxonomy/locations",
    title: "Locations",
    description: "Country, state, city, and area registry.",
  },
  {
    href: "/admin/taxonomy/host-types",
    title: "Host types",
    description: "DJ, comedy collective, tech community, and more.",
  },
  {
    href: "/admin/taxonomy/venue-types",
    title: "Venue types",
    description: "Club, outdoor, campus hall, hybrid online.",
  },
  {
    href: "/admin/categories",
    title: "Legacy categories",
    description: "Previous event_categories admin (being migrated).",
  },
];

export default function AdminTaxonomyHomePage() {
  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin"
        title="Taxonomy"
        description="Manage marketplace vocabulary without breaking live hubs. Archive instead of delete."
        actions={
          <Link href="/admin">
            <Button variant="secondary">Admin home</Button>
          </Link>
        }
      >
        <WorkspaceNavGrid items={LINKS} />
      </DashboardShell>
    </RequireAuth>
  );
}
