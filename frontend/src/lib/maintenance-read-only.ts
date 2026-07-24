import type { PublicMaintenanceStatus } from "@/lib/maintenance-api";

/** True when global read-only or a named section is read-only / hard maintenance. */
export function isWriteBlocked(
  status: PublicMaintenanceStatus | null | undefined,
  sectionKey?: string,
): boolean {
  if (!status) return false;
  if (status.mode === "active" || status.mode === "read_only") return true;
  if (!sectionKey || !status.sections?.length) return false;
  return status.sections.some(
    (s) => s.key === sectionKey && (s.mode === "maintenance" || s.mode === "read_only"),
  );
}

/** Disable interactive write controls when platform/section blocks writes. */
export function writeControlProps(
  status: PublicMaintenanceStatus | null | undefined,
  sectionKey?: string,
): { disabled: boolean; title?: string } {
  if (!isWriteBlocked(status, sectionKey)) return { disabled: false };
  return {
    disabled: true,
    title:
      status?.mode === "read_only"
        ? "Read-only mode — changes disabled"
        : "Unavailable during maintenance",
  };
}
