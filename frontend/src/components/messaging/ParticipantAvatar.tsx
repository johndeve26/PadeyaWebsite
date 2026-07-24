import { Media } from "@/components/ui";
import { cn } from "@/lib/cn";

export function ParticipantAvatar({
  name,
  avatarUrl,
  size = "md",
  className = "",
}: {
  name: string;
  avatarUrl?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const dim =
    size === "sm" ? "h-8 w-8 text-[10px]" : size === "lg" ? "h-12 w-12 text-sm" : "h-10 w-10 text-xs";
  const initial = (name || "?").trim().slice(0, 1).toUpperCase() || "?";

  if (avatarUrl) {
    return (
      <span
        className={cn(
          "relative inline-flex shrink-0 overflow-hidden rounded-full border border-border bg-surface-muted",
          dim,
          className,
        )}
      >
        <Media src={avatarUrl} alt="" className="h-full w-full" />
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-ink font-extrabold text-primary",
        dim,
        className,
      )}
      aria-hidden
    >
      {initial}
    </span>
  );
}
