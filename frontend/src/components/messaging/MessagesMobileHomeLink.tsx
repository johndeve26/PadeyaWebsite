import Link from "next/link";

import { cn } from "@/lib/cn";

/** Mini escape hatch to workspace home from full-screen messages (mobile only). */
export function MessagesMobileHomeLink({
  mode,
  className,
}: {
  mode: "fan" | "host";
  className?: string;
}) {
  const href = mode === "host" ? "/host" : "/dashboard";
  const label = mode === "host" ? "Host home" : "Dashboard";

  return (
    <Link
      href={href}
      className={cn(
        "inline-flex shrink-0 items-center rounded-[var(--radius-sm)] border border-border bg-surface-muted/80 px-2 py-1 text-[11px] font-bold text-muted-foreground hover:text-foreground md:hidden dark:bg-surface-inset/80",
        className,
      )}
      aria-label={`Back to ${label}`}
    >
      ← {mode === "host" ? "Host" : "Home"}
    </Link>
  );
}
