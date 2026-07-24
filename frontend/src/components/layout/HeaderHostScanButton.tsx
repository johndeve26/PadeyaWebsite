"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { useActiveHostWorkspaceForScan } from "@/hooks/useActiveHostWorkspaceForScan";
import { cn } from "@/lib/cn";
import { hostScanHeaderActions } from "@/lib/host-scanner-entry";

/** Mobile-only door + merch scan shortcuts in the site header. */
export function HeaderHostScanButton({
  tone = "default",
}: {
  tone?: "default" | "onDark";
}) {
  const { user } = useAuth();
  const pathname = usePathname() ?? "";
  const workspace = useActiveHostWorkspaceForScan();
  const actions = hostScanHeaderActions(user, pathname, workspace ?? null);

  if (workspace === undefined || actions.length === 0) return null;

  const linkClass = cn(
    "inline-flex h-11 min-w-0 max-w-[6.75rem] flex-1 items-center justify-center rounded-[var(--radius-sm)] border px-1.5 text-[10px] font-bold leading-tight sm:max-w-[7.25rem] sm:text-[11px]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2",
    tone === "onDark"
      ? "border-primary/50 bg-primary/25 text-paper hover:bg-primary/35 focus-visible:ring-offset-ink"
      : "border-primary/45 bg-primary/15 text-foreground hover:border-primary hover:bg-primary/25 focus-visible:ring-offset-background",
  );

  return (
    <div className="flex max-w-[14rem] shrink-0 items-center gap-1 md:hidden">
      {actions.map((action) => (
        <Link
          key={action.id}
          href={action.href}
          className={linkClass}
          aria-label={action.label}
        >
          {action.label}
        </Link>
      ))}
    </div>
  );
}
