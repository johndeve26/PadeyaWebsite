"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { CreateEventCta } from "@/components/layout/CreateEventCta";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button, Logo } from "@/components/ui";
import { userHasRole } from "@/lib/auth/permissions";
import { cn } from "@/lib/cn";

import {
  MOBILE_LEARN_NAV,
  MOBILE_SUPPORT_NAV,
  PUBLIC_NAV,
  isNavLinkActive,
  isPublicNavActive,
} from "./headerNav";
import { useHeaderAccess } from "./HeaderWorkspaceButton";

function subscribeNoop() {
  return () => {};
}

function useIsClient() {
  return useSyncExternalStore(subscribeNoop, () => true, () => false);
}

export function HeaderMobileDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { user, authInitialized, logout, isImpersonating } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const { isAdmin, hasHostWorkspace } = useHeaderAccess(user, isImpersonating);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const mounted = useIsClient();

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const panel = panelRef.current;
    const closeBtn = panel?.querySelector<HTMLElement>("[data-mobile-close]");
    closeBtn?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel) return;
      const nodes = [
        ...panel.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ].filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null);
      if (nodes.length === 0) return;
      const first = nodes[0]!;
      const last = nodes[nodes.length - 1]!;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!mounted || !open) return null;

  const linkClass = (active: boolean) =>
    cn(
      "block rounded-[var(--radius-sm)] px-3 py-3.5 text-base font-semibold transition-colors",
      active
        ? "bg-primary/15 text-primary"
        : "text-paper/85 hover:bg-paper/8 hover:text-paper",
    );

  const panel = (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-[100] flex flex-col overflow-x-hidden bg-ink text-paper xl:hidden"
    >
      <div className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-paper/10 px-4 sm:h-[4.25rem] sm:px-5">
        <Link
          href="/"
          aria-label="Pàdéyá home"
          className="inline-flex shrink-0"
          onClick={onClose}
        >
          <Logo variant="dark" height={28} href="" />
        </Link>
        <p id={titleId} className="sr-only">
          Site menu
        </p>
        <button
          type="button"
          data-mobile-close
          className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-sm)] border border-paper/20 text-paper transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-label="Close menu"
          onClick={onClose}
        >
          <span className="relative block h-3.5 w-4" aria-hidden>
            <span className="absolute left-0 top-1.5 h-0.5 w-4 rotate-45 bg-current" />
            <span className="absolute left-0 top-1.5 h-0.5 w-4 -rotate-45 bg-current" />
          </span>
        </button>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden px-3 py-4 sm:px-4">
        <div className="space-y-0.5">
          <p className="px-3 pb-2 text-xs font-bold uppercase tracking-[0.14em] text-paper/45">
            Discover
          </p>
          {PUBLIC_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={linkClass(isPublicNavActive(item.href, pathname))}
              onClick={onClose}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="mt-5 space-y-0.5 border-t border-paper/10 pt-5">
          <p className="px-3 pb-2 text-xs font-bold uppercase tracking-[0.14em] text-paper/45">
            Learn
          </p>
          {MOBILE_LEARN_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={linkClass(isNavLinkActive(item.href, pathname))}
              onClick={onClose}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="mt-5 space-y-0.5 border-t border-paper/10 pt-5">
          <p className="px-3 pb-2 text-xs font-bold uppercase tracking-[0.14em] text-paper/45">
            Support
          </p>
          {MOBILE_SUPPORT_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={linkClass(isNavLinkActive(item.href, pathname))}
              onClick={onClose}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="mt-5 space-y-0.5 border-t border-paper/10 pt-5">
          <p className="px-3 pb-2 text-xs font-bold uppercase tracking-[0.14em] text-paper/45">
            Account
          </p>
          {authInitialized && user ? (
            <>
              <Link
                href="/dashboard"
                className={linkClass(false)}
                onClick={onClose}
              >
                Personal dashboard
              </Link>
              {hasHostWorkspace ? (
                <Link
                  href="/host"
                  className={linkClass(false)}
                  onClick={onClose}
                >
                  {userHasRole(user, "host_staff") && !userHasRole(user, "host")
                    ? "Staff workspace"
                    : "Host workspace"}
                </Link>
              ) : null}
              {isAdmin ? (
                <Link
                  href="/admin"
                  className={linkClass(false)}
                  onClick={onClose}
                >
                  Admin panel
                </Link>
              ) : null}
              <Link
                href="/dashboard/tickets"
                className={linkClass(false)}
                onClick={onClose}
              >
                Tickets
              </Link>
              <Link
                href="/dashboard/messages"
                className={linkClass(false)}
                onClick={onClose}
              >
                Messages
              </Link>
              <Link
                href="/dashboard/settings"
                className={linkClass(false)}
                onClick={onClose}
              >
                Settings
              </Link>
            </>
          ) : authInitialized && pathname !== "/login" ? (
            <Link href="/login" className={linkClass(false)} onClick={onClose}>
              Log in
            </Link>
          ) : null}
        </div>

        <div className="mt-auto space-y-3 border-t border-paper/10 px-1 pb-6 pt-5">
          <div className="px-2 [&_button]:border-paper/20 [&_button]:text-paper">
            <ThemeToggle className="w-full" />
          </div>
          <CreateEventCta
            mobile
            className="block rounded-[var(--radius-sm)] bg-primary px-3 py-3.5 text-center text-base font-bold text-primary-foreground"
            onNavigate={onClose}
          />
          {authInitialized && user ? (
            <Button
              variant="ghost"
              className="w-full justify-start px-3 py-3.5 text-base font-semibold text-paper/85 hover:bg-paper/8 hover:text-paper"
              onClick={() => {
                onClose();
                void logout().then(() => router.push("/"));
              }}
            >
              Log out
            </Button>
          ) : null}
        </div>
      </nav>
    </div>
  );

  return createPortal(panel, document.body);
}
