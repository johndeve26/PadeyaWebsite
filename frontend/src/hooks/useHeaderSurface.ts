"use client";

import { usePathname } from "next/navigation";
import { useLayoutEffect, useState } from "react";

import { HEADER_DARK_SURFACE } from "@/components/layout/headerSurface";

/**
 * Detects whether the sticky marketing header currently sits over a dark
 * full-bleed surface (`data-header-surface="dark"`), and whether the page
 * has scrolled enough to switch the header to a solid sticky bar.
 */
export function useHeaderSurface(enabled: boolean) {
  const pathname = usePathname();
  const [overDark, setOverDark] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useLayoutEffect(() => {
    if (!enabled) return;

    const measure = () => {
      const headerEl = document.querySelector("header");
      const headerH = headerEl?.getBoundingClientRect().height ?? 64;
      const bandBottom = headerH + 8;
      const nodes = document.querySelectorAll(
        `[data-header-surface="${HEADER_DARK_SURFACE}"]`,
      );
      let dark = false;
      for (const node of nodes) {
        const rect = node.getBoundingClientRect();
        if (rect.top < bandBottom && rect.bottom > 0) {
          dark = true;
          break;
        }
      }
      setOverDark(dark);
      setScrolled(window.scrollY > 12);
    };

    const raf = window.requestAnimationFrame(measure);
    window.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    const ro = new ResizeObserver(measure);
    ro.observe(document.documentElement);

    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
      ro.disconnect();
    };
  }, [enabled, pathname]);

  return {
    overDark: enabled ? overDark : false,
    scrolled: enabled ? scrolled : false,
  };
}
