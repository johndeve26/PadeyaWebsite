"use client";

import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { buildPathBreadcrumbs } from "@/lib/breadcrumbs";
import { cn } from "@/lib/cn";
import { fetchEventById } from "@/lib/events-api";

type Props = {
  homeLabel: string;
  homeHref: string;
  className?: string;
};

export function WorkspaceBreadcrumbs({
  homeLabel,
  homeHref,
  className = "",
}: Props) {
  const pathname = usePathname() || homeHref;
  const built = useMemo(
    () => buildPathBreadcrumbs(pathname, { homeLabel, homeHref }),
    [pathname, homeLabel, homeHref],
  );

  const [resolvedTitles, setResolvedTitles] = useState<Record<string, string>>(
    {},
  );

  const eventIds = useMemo(
    () =>
      built.resolve
        .filter((r) => r.kind === "event")
        .map((r) => r.id)
        .join(","),
    [built.resolve],
  );

  useEffect(() => {
    if (!eventIds) return;
    const ids = eventIds.split(",");
    let active = true;

    void (async () => {
      const entries = await Promise.all(
        ids.map(async (id) => {
          try {
            const event = await fetchEventById(id);
            return [id, event.title] as const;
          } catch {
            return null;
          }
        }),
      );
      if (!active) return;
      setResolvedTitles((prev) => {
        const next = { ...prev };
        for (const entry of entries) {
          if (entry) next[entry[0]] = entry[1];
        }
        return next;
      });
    })();

    return () => {
      active = false;
    };
  }, [eventIds]);

  const items = useMemo(() => {
    if (built.resolve.length === 0) return built.items;
    return built.items.map((item, index) => {
      const job = built.resolve.find((r) => r.index === index);
      if (!job) return item;
      const title = resolvedTitles[job.id];
      return title ? { ...item, label: title } : item;
    });
  }, [built.items, built.resolve, resolvedTitles]);

  return (
    <div
      className={cn(
        "border-b border-border bg-[linear-gradient(180deg,color-mix(in_srgb,var(--primary)_6%,var(--surface-elevated))_0%,var(--surface-elevated)_100%)]",
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-3 px-4 py-2.5 sm:px-6 lg:px-8">
        <span
          aria-hidden
          className="hidden h-4 w-1 shrink-0 rounded-full bg-accent sm:block"
        />
        <Breadcrumb items={items} className="min-w-0 flex-1" />
      </div>
    </div>
  );
}
