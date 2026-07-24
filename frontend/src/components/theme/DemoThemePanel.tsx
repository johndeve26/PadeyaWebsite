"use client";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Card } from "@/components/ui";
import { useTheme } from "@/hooks/useTheme";
import { THEME_LABELS } from "@/lib/theme";

/** Compact theme control for the local demo control center. */
export function DemoThemePanel() {
  const { theme, resolvedTheme, mounted } = useTheme();

  return (
    <Card variant="dark" className="space-y-4">
      <div className="space-y-1">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-accent">
          Appearance
        </p>
        <h3 className="text-lg font-extrabold text-paper">Theme</h3>
        <p className="text-sm text-subtle-foreground">
          Light, dark, or system — persisted in localStorage as{" "}
          <code className="text-accent">padeya-theme</code>.
        </p>
      </div>
      <ThemeToggle variant="segmented" />
      <p className="text-xs text-subtle-foreground">
        {mounted
          ? theme === "system"
            ? `System · resolved ${THEME_LABELS[resolvedTheme].toLowerCase()}`
            : THEME_LABELS[theme]
          : "…"}
      </p>
    </Card>
  );
}
