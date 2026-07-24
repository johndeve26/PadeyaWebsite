"use client";

import { usePathname } from "next/navigation";
import { type ReactNode, useState } from "react";

import {
  WorkspaceNavSections,
  workspaceNavLinkClassName,
} from "@/components/layout/WorkspaceNavSections";
import { Button, Drawer } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  resolveActiveNavItem,
  type NavGroup,
  type NavItem,
} from "@/lib/nav/workspace";

export function DashboardTopbar({
  items,
  groups,
  title = "Menu",
  homeHref,
  toolbar,
  className = "",
}: {
  items: NavItem[];
  /** When set, mobile drawer shows the same grouped nav as the desktop sidebar. */
  groups?: NavGroup[];
  title?: string;
  /** Role-aware workspace home from shell — used for active route highlighting. */
  homeHref?: string;
  toolbar?: ReactNode;
  className?: string;
}) {
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const activeHomeHref = homeHref ?? items[0]?.href;
  const sections = groups?.length ? groups : [{ label: "", items }];
  const activeItem =
    resolveActiveNavItem(pathname, items, activeHomeHref) ?? items[0];
  const sectionCount = sections.reduce(
    (sum, section) => sum + section.items.length,
    0,
  );

  return (
    <>
      <div
        className={cn(
          "relative border-b border-primary/25 bg-gradient-to-b from-primary/12 to-card md:hidden dark:from-primary/10 dark:to-surface-elevated",
          className,
        )}
      >
        {toolbar ? (
          <div className="border-b border-border/80 px-3 py-2">{toolbar}</div>
        ) : null}
        <div className="space-y-2 px-3 py-2.5">
          <Button
            type="button"
            variant="primary"
            size="sm"
            className="h-11 w-full justify-center gap-2.5 border-2 border-primary font-extrabold shadow-[var(--shadow-soft)]"
            onClick={() => setDrawerOpen(true)}
            aria-expanded={drawerOpen}
            aria-controls="workspace-mobile-nav"
            aria-label={`Open dashboard navigation. ${sectionCount} sections available.`}
          >
            <span className="relative block h-3.5 w-4 shrink-0" aria-hidden>
              <span className="absolute left-0 top-0 h-0.5 w-4 rounded-full bg-primary-foreground" />
              <span className="absolute left-0 top-[6px] h-0.5 w-4 rounded-full bg-primary-foreground" />
              <span className="absolute left-0 top-[12px] h-0.5 w-4 rounded-full bg-primary-foreground" />
            </span>
            Dashboard menu
            <span className="rounded-full bg-primary-foreground/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary-foreground">
              {sectionCount} links
            </span>
          </Button>
          <div className="min-w-0 px-1 text-center">
            <p className="truncate text-sm font-semibold text-foreground">
              {activeItem?.label ?? title}
            </p>
            <p className="truncate text-[0.7rem] text-muted-foreground">
              Tap the menu for all {title} sections
            </p>
          </div>
        </div>
      </div>

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Dashboard menu"
        description={`Jump to any ${title} section — overview, tickets, messages, settings, and more.`}
        className="md:hidden"
      >
        <nav
          id="workspace-mobile-nav"
          className="flex min-w-0 w-full flex-col gap-4 overflow-x-hidden"
          aria-label="Dashboard navigation"
        >
          <WorkspaceNavSections
            sections={sections}
            pathname={pathname}
            homeHref={activeHomeHref}
            workspaceTitle={title}
            onNavigate={() => setDrawerOpen(false)}
            linkClassName={workspaceNavLinkClassName}
            labelPaddingClassName="px-1"
          />
        </nav>
      </Drawer>
    </>
  );
}
