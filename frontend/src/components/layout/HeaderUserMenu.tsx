"use client";

import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import type { User } from "@/lib/auth/types";
import { userHasRole } from "@/lib/auth/permissions";
import { cn } from "@/lib/cn";

import { HeaderDropdown, type HeaderMenuItem } from "./HeaderDropdown";
import { useHeaderAccess } from "./HeaderWorkspaceButton";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

export function HeaderUserMenu({
  user,
  tone = "default",
}: {
  user: User;
  tone?: "default" | "onDark";
}) {
  const { logout, isImpersonating } = useAuth();
  const router = useRouter();
  const { isAdmin, hasHostWorkspace } = useHeaderAccess(user, isImpersonating);

  const items: HeaderMenuItem[] = [
    { id: "personal", label: "Personal dashboard", href: "/dashboard" },
  ];
  if (hasHostWorkspace) {
    items.push({
      id: "host",
      label:
        userHasRole(user, "host_staff") && !userHasRole(user, "host")
          ? "Staff workspace"
          : "Host workspace",
      href: "/host",
    });
  }
  if (isAdmin) {
    items.push({ id: "admin", label: "Admin panel", href: "/admin" });
  }
  items.push(
    { id: "tickets", label: "Tickets", href: "/dashboard/tickets" },
    { id: "messages", label: "Messages", href: "/dashboard/messages" },
    { id: "settings", label: "Settings", href: "/dashboard/settings" },
    { id: "support", label: "Support", href: "/support" },
    {
      id: "logout",
      label: "Log out",
      danger: true,
      onSelect: () => {
        void logout().then(() => router.push("/"));
      },
    },
  );

  return (
    <HeaderDropdown
      ariaLabel="Account menu"
      align="right"
      tone={tone}
      label={
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[0.7rem] font-bold",
            tone === "onDark"
              ? "bg-paper text-ink"
              : "bg-ink text-primary",
          )}
          aria-hidden
        >
          {initials(user.full_name)}
        </span>
      }
      items={items}
    />
  );
}
