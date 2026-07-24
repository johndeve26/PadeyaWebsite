"use client";

import { type ReactNode, useEffect } from "react";

/** Hide workspace breadcrumbs on mobile and align the fixed messages pane. */
export function MessagesMobileChrome({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.classList.add("messages-mobile-chrome");
    return () => {
      document.documentElement.classList.remove("messages-mobile-chrome");
    };
  }, []);

  return children;
}
