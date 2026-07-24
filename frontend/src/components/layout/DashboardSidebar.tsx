"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import {
  WorkspaceNavSections,
  workspaceNavLinkClassName,
} from "@/components/layout/WorkspaceNavSections";
import { cn } from "@/lib/cn";
import type { NavGroup, NavItem } from "@/lib/nav/workspace";

export function DashboardSidebar({
  items,
  groups,
  title,
  homeHref,
  toolbar,
  className = "",
}: {
  items: NavItem[];
  /** When set, render grouped labels in the desktop sidebar. */
  groups?: NavGroup[];
  title: string;
  /**
   * Role-aware workspace home (from shell). Do not infer from `items[0]` —
   * desk-filtered nav may start with Events, not Overview.
   */
  homeHref?: string;
  toolbar?: ReactNode;
  className?: string;
}) {
  const pathname = usePathname();
  const activeHomeHref = homeHref ?? items[0]?.href;
  const sections = groups?.length
    ? groups
    : [{ label: "", items }];

  // Vertical workspace chrome: stable desktop width, stacked groups, full-width rows.
  // Do not introduce horizontal / wrapped / multi-column nav lists here.
  return (
    <aside
      className={cn(
        "hidden w-80 min-w-80 max-w-80 shrink-0 grow-0 basis-80 self-stretch border-r border-border bg-[linear-gradient(180deg,var(--surface-elevated)_0%,var(--surface)_100%)] md:block",
        className,
      )}
    >
      <div className="sticky top-16 flex max-h-[calc(100dvh-4rem)] min-w-0 flex-col gap-4 overflow-x-hidden overflow-y-auto px-3 py-6">
        <p className="shrink-0 truncate px-3 text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
          {title}
        </p>
        {toolbar ? (
          <div className="min-w-0 w-full shrink-0 px-1">{toolbar}</div>
        ) : null}
        <nav
          className="flex min-w-0 w-full flex-1 flex-col gap-4"
          aria-label={`${title} navigation`}
        >
          <WorkspaceNavSections
            sections={sections}
            pathname={pathname}
            homeHref={activeHomeHref}
            workspaceTitle={title}
            linkClassName={workspaceNavLinkClassName}
            labelPaddingClassName="px-3"
          />
        </nav>
      </div>
    </aside>
  );
}
