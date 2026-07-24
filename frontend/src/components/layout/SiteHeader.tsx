"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { CreateEventCta } from "@/components/layout/CreateEventCta";
import { HeaderHostScanButton } from "@/components/layout/HeaderHostScanButton";
import { HeaderMobileDrawer } from "@/components/layout/HeaderMobileDrawer";
import { HeaderResourcesDropdown } from "@/components/layout/HeaderResourcesDropdown";
import { HeaderUserMenu } from "@/components/layout/HeaderUserMenu";
import {
  PUBLIC_NAV,
  isPublicNavActive,
} from "@/components/layout/headerNav";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button, Container, Logo } from "@/components/ui";
import { useHeaderSurface } from "@/hooks/useHeaderSurface";
import { cn } from "@/lib/cn";

import { isWorkspacePath } from "./workspacePath";

const navLinkBase =
  "rounded-[var(--radius-sm)] px-2.5 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 xl:px-3";

export function SiteHeader() {
  const { user, authInitialized, isImpersonating } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const workspace = isWorkspacePath(pathname);
  const marketing = !workspace;
  const { overDark, scrolled } = useHeaderSurface(marketing);
  const containerWidth = workspace ? "full" : "default";

  const authMarketingPage =
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/forgot-password" ||
    pathname === "/reset-password";

  // Transparent + light nav only at scroll top over a dark hero; once scrolled, solid bar.
  const onDark =
    marketing && !scrolled && (authMarketingPage || overDark);
  const showScrolledBar = marketing && scrolled;

  useEffect(() => {
    const mode = marketing ? "transparent" : "solid";
    document.documentElement.dataset.headerMode = mode;
    return () => {
      delete document.documentElement.dataset.headerMode;
    };
  }, [marketing]);

  const navLinkActive = onDark
    ? "bg-paper text-ink"
    : "bg-ink text-paper";
  const navLinkInactive = onDark
    ? "text-paper/80 hover:bg-paper/10 hover:text-paper"
    : "text-muted-foreground hover:bg-surface-muted hover:text-foreground";
  const chromeControl = onDark
    ? "border-paper/30 bg-transparent text-paper hover:border-paper/55 hover:bg-paper/10"
    : undefined;

  return (
    <header
      className={cn(
        "sticky z-40 transition-[background-color,border-color,backdrop-filter,box-shadow] duration-200",
        isImpersonating
          ? "top-[var(--impersonation-banner-height,0px)]"
          : "top-0",
        workspace
          ? "border-b border-border bg-card/95 backdrop-blur-md dark:bg-surface-elevated/95"
          : showScrolledBar
            ? "border-b border-border bg-card/95 shadow-[var(--shadow-soft)] backdrop-blur-md dark:bg-surface-elevated/95"
            : onDark
              ? "border-b border-transparent bg-transparent"
              : "border-b border-transparent bg-transparent",
      )}
    >
      <Container
        width={containerWidth}
        className="flex h-16 min-w-0 items-center justify-between gap-3 sm:h-[4.25rem] sm:gap-4"
      >
        <div className="flex min-w-0 items-center gap-3 xl:gap-8">
          <Logo
            variant={onDark ? "dark" : "auto"}
            priority
            height={32}
            className="shrink-0"
          />
          <nav
            className="hidden items-center gap-0.5 xl:flex"
            aria-label="Primary"
          >
            {PUBLIC_NAV.map((item) => {
              const active = isPublicNavActive(item.href, pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    navLinkBase,
                    active ? navLinkActive : navLinkInactive,
                    onDark
                      ? "focus-visible:ring-offset-ink"
                      : "focus-visible:ring-offset-background",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
            <HeaderResourcesDropdown tone={onDark ? "onDark" : "default"} />
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <HeaderHostScanButton tone={onDark ? "onDark" : "default"} />
          <ThemeToggle compact tone={onDark ? "onDark" : "default"} />

          {!authInitialized ? null : user ? (
            <NotificationBell tone={onDark ? "onDark" : "default"} />
          ) : null}

          {authInitialized && !user && pathname !== "/login" ? (
            <Link href="/login" className="hidden xl:inline-flex">
              <Button
                variant="ghost"
                size="sm"
                className={
                  onDark
                    ? "text-paper hover:bg-paper/10 hover:text-paper"
                    : undefined
                }
              >
                Log in
              </Button>
            </Link>
          ) : null}

          <span className="hidden xl:inline-flex">
            <CreateEventCta />
          </span>

          {authInitialized && user ? (
            <span className="hidden xl:inline-flex">
              <HeaderUserMenu
                user={user}
                tone={onDark ? "onDark" : "default"}
              />
            </span>
          ) : null}

          <button
            type="button"
            className={cn(
              "inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-sm)] border text-sm font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 xl:hidden",
              chromeControl ??
                "border-border text-foreground hover:border-border-strong focus-visible:ring-offset-background",
              onDark && "focus-visible:ring-offset-ink",
            )}
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            <span className="relative block h-3.5 w-4" aria-hidden>
              <span
                className={cn(
                  "absolute left-0 h-0.5 w-4 transition-all",
                  onDark ? "bg-paper" : "bg-foreground",
                  mobileOpen ? "top-1.5 rotate-45" : "top-0",
                )}
              />
              <span
                className={cn(
                  "absolute left-0 top-1.5 h-0.5 w-4 transition-opacity",
                  onDark ? "bg-paper" : "bg-foreground",
                  mobileOpen ? "opacity-0" : "opacity-100",
                )}
              />
              <span
                className={cn(
                  "absolute left-0 h-0.5 w-4 transition-all",
                  onDark ? "bg-paper" : "bg-foreground",
                  mobileOpen ? "top-1.5 -rotate-45" : "top-3",
                )}
              />
            </span>
          </button>
        </div>
      </Container>

      <HeaderMobileDrawer
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
      />
    </header>
  );
}
