"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import type { User } from "@/lib/auth/types";
import { canAccessAdminPanel } from "@/lib/auth/workspace-access";
import { userHasRole } from "@/lib/auth/permissions";
import { fetchHostWorkspaces } from "@/lib/hosts-api";
import { cn } from "@/lib/cn";

import {
  HeaderDropdown,
  workspaceMenuActive,
  type HeaderMenuItem,
} from "./HeaderDropdown";

function isAdminUser(user: User, isImpersonating: boolean): boolean {
  return canAccessAdminPanel(user, isImpersonating);
}

function isHostRole(user: User): boolean {
  return userHasRole(user, "host", "host_staff");
}

/**
 * Role-aware workspace entry: Personal link, or Host/Admin dropdown.
 * Never dumps long names into the main nav.
 */
export function HeaderWorkspaceButton({
  user,
  isImpersonating,
  tone = "default",
}: {
  user: User;
  isImpersonating: boolean;
  tone?: "default" | "onDark";
}) {
  const pathname = usePathname();
  const hostRole = isHostRole(user);
  const [fetchedHostWs, setFetchedHostWs] = useState<{
    userId: string;
    value: boolean;
  } | null>(null);

  useEffect(() => {
    if (hostRole) return;
    const userId = user.id;
    let alive = true;
    void fetchHostWorkspaces()
      .then((rows) => {
        if (alive) setFetchedHostWs({ userId, value: rows.length > 0 });
      })
      .catch(() => {
        if (alive) setFetchedHostWs({ userId, value: false });
      });
    return () => {
      alive = false;
    };
  }, [user, hostRole]);

  const hasHostWorkspace =
    hostRole ||
    (fetchedHostWs?.userId === user.id && fetchedHostWs.value);

  const admin = isAdminUser(user, isImpersonating);

  if (admin) {
    const items: HeaderMenuItem[] = [
      { id: "personal", label: "Personal dashboard", href: "/dashboard" },
      { id: "admin", label: "Admin panel", href: "/admin" },
    ];
    if (hasHostWorkspace) {
      items.push({ id: "host", label: "Host workspace", href: "/host" });
    }
    return (
      <HeaderDropdown
        label="Admin"
        ariaLabel="Admin workspace menu"
        items={items}
        active={workspaceMenuActive(pathname, "admin")}
        className="hidden xl:inline-flex"
        tone={tone}
      />
    );
  }

  if (hasHostWorkspace) {
    const staffOnly = userHasRole(user, "host_staff") && !userHasRole(user, "host");
    return (
      <HeaderDropdown
        label={staffOnly ? "Staff" : "Host"}
        ariaLabel={staffOnly ? "Staff workspace menu" : "Host workspace menu"}
        items={[
          { id: "personal", label: "Personal dashboard", href: "/dashboard" },
          { id: "host", label: "Host workspace", href: "/host" },
        ]}
        active={
          workspaceMenuActive(pathname, "host") ||
          workspaceMenuActive(pathname, "personal")
        }
        className="hidden xl:inline-flex"
        tone={tone}
      />
    );
  }

  return (
    <Link
      href="/dashboard"
      className={cn(
        "hidden h-10 items-center rounded-[var(--radius-sm)] px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 xl:inline-flex",
        tone === "onDark"
          ? cn(
              "focus-visible:ring-offset-ink",
              workspaceMenuActive(pathname, "personal")
                ? "bg-paper text-ink"
                : "text-paper/85 hover:bg-paper/10 hover:text-paper",
            )
          : cn(
              "focus-visible:ring-offset-background",
              workspaceMenuActive(pathname, "personal")
                ? "bg-ink text-paper"
                : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
            ),
      )}
    >
      Personal
    </Link>
  );
}

export function useHeaderAccess(user: User | null, isImpersonating: boolean) {
  const hostRole = Boolean(user && isHostRole(user));
  const [fetchedHostWs, setFetchedHostWs] = useState<{
    userId: string;
    value: boolean;
  } | null>(null);

  useEffect(() => {
    if (!user || hostRole) return;
    const userId = user.id;
    let alive = true;
    void fetchHostWorkspaces()
      .then((rows) => {
        if (alive) setFetchedHostWs({ userId, value: rows.length > 0 });
      })
      .catch(() => {
        if (alive) setFetchedHostWs({ userId, value: false });
      });
    return () => {
      alive = false;
    };
  }, [user, hostRole]);

  const hasHostWorkspace = Boolean(
    user &&
      (hostRole ||
        (fetchedHostWs?.userId === user.id && fetchedHostWs.value)),
  );

  return {
    isAdmin: Boolean(user && isAdminUser(user, isImpersonating)),
    hasHostWorkspace,
  };
}
