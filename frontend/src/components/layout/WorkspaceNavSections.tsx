"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { NavLabel } from "@/components/layout/NavLabel";
import {
  resolveFavoriteNavItems,
  useWorkspaceNavPreferences,
} from "@/hooks/useWorkspaceNavPreferences";
import { cn } from "@/lib/cn";
import { isNavItemActive, type NavGroup, type NavItem } from "@/lib/nav/workspace";

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      aria-hidden
      className={cn("h-3 w-3 shrink-0 text-muted-foreground/70", className)}
      fill="none"
    >
      <path
        d="M4 6l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden className="h-3.5 w-3.5" fill="none">
      <path
        d="M8 2.5l1.55 3.14 3.47.5-2.51 2.45.59 3.45L8 10.68l-3.1 1.36.59-3.45-2.51-2.45 3.47-.5L8 2.5Z"
        stroke="currentColor"
        strokeWidth="1.35"
        strokeLinejoin="round"
        fill={filled ? "currentColor" : "none"}
      />
    </svg>
  );
}

function PinIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden className="h-3.5 w-3.5" fill="none">
      <path
        d="M9.25 2.75 11 4.5l-1.5 1.5 2.75 2.75-1.06 1.06-2.1-.65-.65 2.1-1.06-1.06L5.5 8.25 4 6.75l1.75-1.75L4 3.25l1.06-1.06L8 4.19l1.19-1.19Z"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinejoin="round"
        fill={filled ? "currentColor" : "none"}
      />
    </svg>
  );
}

function NavSectionLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground/50",
        className,
      )}
    >
      {children}
    </span>
  );
}

function NavRow({
  item,
  active,
  onNavigate,
  linkClassName,
  isFavorite,
  isPinned,
  onToggleFavorite,
  onTogglePin,
}: {
  item: NavItem;
  active: boolean;
  onNavigate?: () => void;
  linkClassName: (active: boolean) => string;
  isFavorite: boolean;
  isPinned: boolean;
  onToggleFavorite: () => void;
  onTogglePin: () => void;
}) {
  return (
    <li className="group/navrow w-full">
      <div className="relative flex min-w-0 items-stretch">
        <Link
          href={item.href}
          onClick={onNavigate}
          className={cn(linkClassName(active), "min-w-0 flex-1 pr-16")}
        >
          <NavLabel item={item} active={active} />
        </Link>
        <div
          className={cn(
            "absolute inset-y-0 right-1 flex items-center gap-0.5",
            "opacity-0 transition-opacity group-hover/navrow:opacity-100 group-focus-within/navrow:opacity-100",
            (isFavorite || isPinned) && "opacity-100",
          )}
        >
          {isFavorite ? (
            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onTogglePin();
              }}
              className={cn(
                "inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] transition-colors",
                focusRing,
                active
                  ? "text-paper/80 hover:bg-paper/15 hover:text-paper"
                  : "text-muted-foreground/70 hover:bg-surface-muted hover:text-foreground",
                isPinned && (active ? "text-paper" : "text-foreground"),
              )}
              aria-label={isPinned ? "Unpin from favorites" : "Pin to top of favorites"}
              aria-pressed={isPinned}
            >
              <PinIcon filled={isPinned} />
            </button>
          ) : null}
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onToggleFavorite();
            }}
            className={cn(
              "inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] transition-colors",
              focusRing,
              active
                ? "text-paper/80 hover:bg-paper/15 hover:text-paper"
                : "text-muted-foreground/70 hover:bg-surface-muted hover:text-foreground",
              isFavorite && (active ? "text-paper" : "text-primary"),
            )}
            aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
            aria-pressed={isFavorite}
          >
            <StarIcon filled={isFavorite} />
          </button>
        </div>
      </div>
    </li>
  );
}

function NavItemList({
  items,
  siblings,
  pathname,
  homeHref,
  onNavigate,
  linkClassName,
  isFavorite,
  isPinned,
  onToggleFavorite,
  onTogglePin,
}: {
  items: NavItem[];
  /** Full workspace nav for parent/sibling active resolution. */
  siblings: NavItem[];
  pathname: string;
  homeHref: string | undefined;
  onNavigate?: () => void;
  linkClassName: (active: boolean) => string;
  isFavorite: (href: string) => boolean;
  isPinned: (href: string) => boolean;
  onToggleFavorite: (href: string) => void;
  onTogglePin: (href: string) => void;
}) {
  // One full-width row per item; stack only — never wrap or multi-column.
  return (
    <ul className="m-0 flex w-full list-none flex-col space-y-1 p-0">
      {items.map((item) => {
        const active = isNavItemActive(pathname, item, homeHref, siblings);
        return (
          <NavRow
            key={item.href}
            item={item}
            active={active}
            onNavigate={onNavigate}
            linkClassName={linkClassName}
            isFavorite={isFavorite(item.href)}
            isPinned={isPinned(item.href)}
            onToggleFavorite={() => onToggleFavorite(item.href)}
            onTogglePin={() => onTogglePin(item.href)}
          />
        );
      })}
    </ul>
  );
}

export function WorkspaceNavSections({
  sections,
  pathname,
  homeHref,
  workspaceTitle,
  onNavigate,
  linkClassName,
  labelPaddingClassName = "px-3",
}: {
  sections: NavGroup[];
  pathname: string;
  homeHref: string | undefined;
  workspaceTitle: string;
  onNavigate?: () => void;
  linkClassName: (active: boolean) => string;
  /** Horizontal padding for section labels (sidebar vs drawer). */
  labelPaddingClassName?: string;
}) {
  const {
    favorites,
    isFavorite,
    isPinned,
    isGroupCollapsed,
    toggleFavorite,
    togglePin,
    toggleGroupCollapsed,
  } = useWorkspaceNavPreferences(workspaceTitle);

  const favoriteItems = resolveFavoriteNavItems(sections, favorites);
  const siblingItems = sections.flatMap((section) => section.items);

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      {favoriteItems.length > 0 ? (
        <section className="min-w-0 w-full">
          <div className={cn("pb-1.5", labelPaddingClassName)}>
            <NavSectionLabel>Favorites</NavSectionLabel>
          </div>
          <NavItemList
            items={favoriteItems}
            siblings={siblingItems}
            pathname={pathname}
            homeHref={homeHref}
            onNavigate={onNavigate}
            linkClassName={linkClassName}
            isFavorite={isFavorite}
            isPinned={isPinned}
            onToggleFavorite={toggleFavorite}
            onTogglePin={togglePin}
          />
        </section>
      ) : null}

      {sections.map((section, index) => {
        const hasBorder = index > 0 || favoriteItems.length > 0;
        const collapsed = section.label
          ? isGroupCollapsed(section.label)
          : false;

        return (
          <section
            key={section.label || "default"}
            className={cn(
              "min-w-0 w-full",
              hasBorder && "border-t border-border pt-4",
            )}
          >
            {section.label ? (
              <button
                type="button"
                onClick={() => toggleGroupCollapsed(section.label)}
                aria-expanded={!collapsed}
                className={cn(
                  "mb-1.5 flex w-full min-w-0 items-center gap-1.5 rounded-[var(--radius-sm)] py-1 text-left transition-colors",
                  labelPaddingClassName,
                  focusRing,
                  "hover:text-foreground",
                )}
              >
                <ChevronIcon
                  className={cn(
                    "transition-transform duration-200",
                    collapsed && "-rotate-90",
                  )}
                />
                <NavSectionLabel>{section.label}</NavSectionLabel>
              </button>
            ) : null}

            {!collapsed ? (
              <NavItemList
                items={section.items}
                siblings={siblingItems}
                pathname={pathname}
                homeHref={homeHref}
                onNavigate={onNavigate}
                linkClassName={linkClassName}
                isFavorite={isFavorite}
                isPinned={isPinned}
                onToggleFavorite={toggleFavorite}
                onTogglePin={togglePin}
              />
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

export const workspaceNavLinkClassName = (active: boolean) =>
  cn(
    "flex min-w-0 w-full items-center justify-between gap-2 rounded-[var(--radius-sm)] px-3 py-2.5 text-sm font-semibold transition-colors",
    focusRing,
    active
      ? "bg-ink text-paper shadow-[var(--shadow-soft)]"
      : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
  );
