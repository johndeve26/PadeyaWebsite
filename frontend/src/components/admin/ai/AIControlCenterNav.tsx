"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const NAV = [
  { href: "/admin/ai", label: "Overview", exact: true },
  { href: "/admin/ai/providers", label: "Providers" },
  { href: "/admin/ai/features", label: "Feature routing" },
  { href: "/admin/ai/usage", label: "Usage" },
  { href: "/admin/ai/logs", label: "Logs" },
  { href: "/admin/ai/safety", label: "Safety" },
  { href: "/admin/ai/settings", label: "Settings" },
] as const;

export function AIControlCenterNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-2 border-b border-border pb-3">
      {NAV.map((item) => {
        const active =
          "exact" in item && item.exact
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded-full px-3 py-1.5 text-sm font-semibold transition",
              active
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-surface-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AIControlCenterHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-bold uppercase tracking-wide text-primary">
        Pàdéyá AI Control Center
      </p>
      <h1 className="text-2xl font-extrabold text-foreground">{title}</h1>
      {description ? (
        <p className="max-w-3xl text-sm text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}
