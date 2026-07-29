"use client";

import { type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { Container } from "@/components/ui";
import type { NavGroup, NavItem } from "@/lib/nav/workspace";

import { DashboardSidebar } from "./DashboardSidebar";
import { DashboardTopbar } from "./DashboardTopbar";
import { HostWorkspaceMobileBottomNav } from "./HostWorkspaceMobileBottomNav";
import { WorkspaceBreadcrumbs } from "./WorkspaceBreadcrumbs";

/** Blog workspace routes use a fixed-height shell so tab panels scroll internally. */
function isBlogImmersiveWorkspace(pathname: string): boolean {
  return /^\/admin\/blog\/(new|[\w-]+\/edit)(\/|$)/.test(pathname);
}

/**
 * Shared chrome for Personal (`/dashboard`), Host (`/host`), Admin, and Support.
 * Nav config is mode-specific — do not concatenate buyer + host items here.
 */
export function WorkspaceShell({
  nav,
  navGroups,
  title,
  homeHref,
  hostMobileNav = false,
  toolbar,
  children,
}: {
  nav: NavItem[];
  navGroups?: NavGroup[];
  title: string;
  /**
   * Workspace home for breadcrumbs + nav active-state roots.
   * Host layouts should pass `hostHomePathForWorkspace(active)` (role-aware).
   */
  homeHref: string;
  /** Host mobile tab bar (Home · Alerts · Inbox · Events). */
  hostMobileNav?: boolean;
  /** Optional control beside nav (e.g. Personal ↔ Host workspace switcher). */
  toolbar?: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname() || "";
  const blogImmersive = isBlogImmersiveWorkspace(pathname);

  return (
    <div className="min-h-[70vh] min-w-0 overflow-x-clip bg-background">
      <DashboardTopbar
        items={nav}
        groups={navGroups}
        title={title}
        homeHref={homeHref}
        toolbar={toolbar}
      />
      <Container
        width="full"
        className="flex min-w-0 !px-0 overflow-x-clip"
      >
        <DashboardSidebar
          items={nav}
          groups={navGroups}
          title={title}
          homeHref={homeHref}
          toolbar={toolbar}
        />
        <div
          className={`flex min-h-0 min-w-0 flex-1 flex-col overflow-x-clip ${
            blogImmersive ? "md:h-[calc(100dvh-var(--site-header-height))]" : ""
          }`}
        >
          <div className="sticky top-0 z-20 shrink-0 px-4 sm:px-6 lg:px-8" data-workspace-breadcrumbs>
            <WorkspaceBreadcrumbs homeLabel={title} homeHref={homeHref} />
          </div>
          <div
            className={
              blogImmersive
                ? "flex min-h-0 flex-1 flex-col overflow-hidden"
                : "flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden"
            }
          >
            {children}
          </div>
          {hostMobileNav ? (
            <HostWorkspaceMobileBottomNav homeHref={homeHref} />
          ) : (
            <div
              className="min-h-[calc(3.5rem+env(safe-area-inset-bottom))] md:min-h-0"
              aria-hidden
            />
          )}
        </div>
      </Container>
    </div>
  );
}
