import { cn } from "@/lib/cn";

type MemoryGalleryEmptyStateProps = {
  message: string;
  className?: string;
};

export function MemoryGalleryEmptyState({
  message,
  className,
}: MemoryGalleryEmptyStateProps) {
  return (
    <p
      className={cn(
        "rounded-xl border border-dashed border-border bg-surface-muted/40 px-4 py-6 text-sm text-muted-foreground",
        className,
      )}
    >
      {message}
    </p>
  );
}
