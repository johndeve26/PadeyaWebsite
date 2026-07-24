"use client";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Card, SectionHeader } from "@/components/ui";
import { useTheme } from "@/hooks/useTheme";
import { THEME_LABELS } from "@/lib/theme";
import { cn } from "@/lib/cn";

/**
 * Account/settings Appearance block — Light / Dark / System.
 * Syncs via ThemeProvider (`padeya-theme` localStorage).
 */
export function ThemeAppearanceCard({ className = "" }: { className?: string }) {
  const { theme, resolvedTheme, mounted } = useTheme();

  return (
    <Card className={cn("max-w-lg space-y-5", className)}>
      <SectionHeader
        eyebrow="Appearance"
        title="Theme preference"
        description="Choose Light, Dark, or System. Saved on this device and applied across Pàdéyá."
      />
      <ThemeToggle variant="segmented" showLabels="always" />
      <p className="text-xs text-muted-foreground" aria-live="polite">
        {mounted
          ? theme === "system"
            ? `System · currently ${THEME_LABELS[resolvedTheme].toLowerCase()}`
            : `${THEME_LABELS[theme]} mode`
          : "Loading theme preference…"}
      </p>
    </Card>
  );
}
