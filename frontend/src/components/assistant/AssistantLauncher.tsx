"use client";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

export function AssistantLauncher({
  onClick,
  label,
  className,
}: {
  onClick: () => void;
  label: string;
  className?: string;
}) {
  return (
    <Button
      type="button"
      variant="primary"
      size="md"
      onClick={onClick}
      aria-label={label}
      className={cn(
        "h-12 min-h-12 rounded-full px-4 shadow-[var(--shadow)] motion-safe:transition-transform motion-safe:duration-200 motion-safe:hover:scale-[1.02] motion-reduce:transition-none",
        className,
      )}
    >
      <span
        className="flex h-6 w-6 items-center justify-center rounded-full bg-ink/10 text-xs font-extrabold text-primary-foreground"
        aria-hidden
      >
        ?
      </span>
      <span className="hidden sm:inline">{label}</span>
    </Button>
  );
}
