"use client";

import Link from "next/link";

import {
  RESOURCES_FEATURED,
  RESOURCES_LEARN,
  RESOURCES_PLATFORM,
  RESOURCES_SUPPORT,
  type NavLink,
  isNavLinkActive,
} from "@/components/layout/headerNav";
import { cn } from "@/lib/cn";

function MegaColumn({
  title,
  items,
  pathname,
  onNavigate,
}: {
  title: string;
  items: readonly NavLink[];
  pathname: string;
  onNavigate: () => void;
}) {
  return (
    <div className="min-w-0">
      <p className="px-1 text-[0.65rem] font-bold uppercase tracking-[0.16em] text-paper/45">
        {title}
      </p>
      <ul className="mt-3 space-y-0.5">
        {items.map((item) => {
          const active = isNavLinkActive(item.href, pathname);
          return (
            <li key={`${item.href}:${item.label}`}>
              <Link
                href={item.href}
                role="menuitem"
                className={cn(
                  "block rounded-[var(--radius-sm)] px-2.5 py-2 transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                  active
                    ? "bg-primary/15 text-primary"
                    : "text-paper/85 hover:bg-paper/8 hover:text-paper",
                )}
                onClick={onNavigate}
              >
                <span className="block text-sm font-semibold">{item.label}</span>
                {item.description ? (
                  <span className="mt-0.5 block text-xs font-medium text-paper/45">
                    {item.description}
                  </span>
                ) : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function ResourcesMegaPanel({
  id,
  pathname,
  onNavigate,
}: {
  id: string;
  pathname: string;
  onNavigate: () => void;
}) {
  return (
    <div
      id={id}
      role="menu"
      aria-label="Resources"
      className={cn(
        "absolute z-50 w-[min(52rem,calc(100vw-1.5rem))]",
        "before:absolute before:inset-x-0 before:-top-[var(--resources-panel-gap,10px)]",
        "before:h-[var(--resources-panel-gap,10px)] before:content-['']",
        "overflow-hidden rounded-[var(--radius-lg)] border border-paper/12",
        "bg-ink text-paper shadow-[var(--shadow)]",
      )}
    >
      <div className="grid gap-6 p-5 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5 lg:p-6">
        <MegaColumn
          title="Learn"
          items={RESOURCES_LEARN}
          pathname={pathname}
          onNavigate={onNavigate}
        />
        <MegaColumn
          title="Support & Safety"
          items={RESOURCES_SUPPORT}
          pathname={pathname}
          onNavigate={onNavigate}
        />
        <MegaColumn
          title="Platform"
          items={RESOURCES_PLATFORM}
          pathname={pathname}
          onNavigate={onNavigate}
        />
        <div className="min-w-0 rounded-[var(--radius-md)] border border-paper/10 bg-paper/5 p-4 sm:col-span-2 lg:col-span-1">
          <p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] text-primary">
            Featured
          </p>
          <p className="mt-3 font-display text-lg font-extrabold tracking-tight text-paper">
            {RESOURCES_FEATURED.title}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-paper/65">
            {RESOURCES_FEATURED.description}
          </p>
          <Link
            href={RESOURCES_FEATURED.cta.href}
            role="menuitem"
            className={cn(
              "mt-4 inline-flex min-h-10 items-center rounded-[var(--radius-sm)]",
              "bg-primary px-3.5 py-2 text-sm font-bold text-primary-foreground",
              "transition-opacity hover:opacity-90",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-ink",
            )}
            onClick={onNavigate}
          >
            {RESOURCES_FEATURED.cta.label}
          </Link>
        </div>
      </div>
    </div>
  );
}
