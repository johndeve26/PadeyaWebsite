"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, SectionHeader, WorkspaceNavGrid } from "@/components/ui";

const cmsItems = [
  {
    href: "/admin/cms/blog",
    title: "Blog posts",
    description: "Draft, publish, and archive platform blog content.",
    meta: "Content",
  },
  {
    href: "/admin/cms/faqs",
    title: "FAQs",
    description: "Help centre questions and answers shown on public pages.",
    meta: "Support",
  },
  {
    href: "/admin/cms/banners",
    title: "Banners",
    description: "Homepage and marketing banner slots with CTA links.",
    meta: "Marketing",
  },
  {
    href: "/admin/cms/browse-tiles",
    title: "Browse tiles",
    description:
      "Homepage interest, city, price, and when tiles — swap images and links.",
    meta: "Homepage",
  },
];

export default function AdminCmsPage() {
  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Content management"
      description="Blog, FAQs, banners, and browse tiles — publish and archive instead of hard delete."
      actions={
        <Link href="/admin/cms/blog/new">
          <Button>New blog post</Button>
        </Link>
      }
    >
      <SectionHeader
        eyebrow="CMS"
        title="Choose a content type"
        description="All changes are audited. Archived content can be restored."
      />
      <WorkspaceNavGrid items={cmsItems} />
    </DashboardShell>
  );
}
