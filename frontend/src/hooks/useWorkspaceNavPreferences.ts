"use client";

import { useCallback, useState } from "react";

import {
  readNavCollapseState,
  readNavFavoritesState,
  writeNavCollapseState,
  writeNavFavoritesState,
  workspaceNavScope,
  type NavCollapseState,
  type NavFavoritesState,
} from "@/lib/nav/nav-preferences";
import type { NavGroup, NavItem } from "@/lib/nav/workspace";

export function resolveFavoriteNavItems(
  sections: NavGroup[],
  favoritesState: NavFavoritesState,
): NavItem[] {
  const itemByHref = new Map<string, NavItem>();
  for (const section of sections) {
    for (const item of section.items) {
      itemByHref.set(item.href, item);
    }
  }

  const validFavorites = favoritesState.favorites.filter((href) =>
    itemByHref.has(href),
  );
  const validPinned = favoritesState.pinned.filter((href) =>
    validFavorites.includes(href),
  );
  const unpinned = validFavorites.filter((href) => !validPinned.includes(href));

  return [...validPinned, ...unpinned].map((href) => itemByHref.get(href)!);
}

export function useWorkspaceNavPreferences(workspaceTitle: string) {
  const scope = workspaceNavScope(workspaceTitle);
  const [collapse, setCollapse] = useState<NavCollapseState>(() =>
    readNavCollapseState(scope),
  );
  const [favorites, setFavorites] = useState<NavFavoritesState>(() =>
    readNavFavoritesState(scope),
  );

  const isGroupCollapsed = useCallback(
    (groupLabel: string) => Boolean(collapse[groupLabel]),
    [collapse],
  );

  const toggleGroupCollapsed = useCallback(
    (groupLabel: string) => {
      setCollapse((prev) => {
        const next = { ...prev };
        if (next[groupLabel]) {
          delete next[groupLabel];
        } else {
          next[groupLabel] = true;
        }
        writeNavCollapseState(scope, next);
        return next;
      });
    },
    [scope],
  );

  const isFavorite = useCallback(
    (href: string) => favorites.favorites.includes(href),
    [favorites.favorites],
  );

  const isPinned = useCallback(
    (href: string) => favorites.pinned.includes(href),
    [favorites.pinned],
  );

  const toggleFavorite = useCallback(
    (href: string) => {
      setFavorites((prev) => {
        const next = prev.favorites.includes(href)
          ? {
              favorites: prev.favorites.filter((h) => h !== href),
              pinned: prev.pinned.filter((h) => h !== href),
            }
          : { ...prev, favorites: [...prev.favorites, href] };
        writeNavFavoritesState(scope, next);
        return next;
      });
    },
    [scope],
  );

  const togglePin = useCallback(
    (href: string) => {
      setFavorites((prev) => {
        let next: NavFavoritesState;
        if (!prev.favorites.includes(href)) {
          next = {
            favorites: [...prev.favorites, href],
            pinned: [...prev.pinned, href],
          };
        } else if (prev.pinned.includes(href)) {
          next = {
            ...prev,
            pinned: prev.pinned.filter((h) => h !== href),
          };
        } else {
          next = { ...prev, pinned: [...prev.pinned, href] };
        }
        writeNavFavoritesState(scope, next);
        return next;
      });
    },
    [scope],
  );

  return {
    favorites,
    isFavorite,
    isPinned,
    isGroupCollapsed,
    toggleFavorite,
    togglePin,
    toggleGroupCollapsed,
  };
}
