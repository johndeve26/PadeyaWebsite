import { apiRequest } from "@/lib/api";
import type { PublicMaintenanceStatus } from "@/lib/maintenance-api";

/**
 * Shared public maintenance status fetch.
 *
 * MaintenanceGate + MaintenanceBanner both mount on every page; without
 * single-flight they issue two concurrent GET /maintenance/status calls.
 *
 * Cache TTL is short so mode changes still surface quickly — not indefinite.
 */
const CACHE_TTL_MS = 15_000;

let inflight: Promise<PublicMaintenanceStatus> | null = null;
let cached: { at: number; value: PublicMaintenanceStatus } | null = null;

/** Test/helper — clears module cache between vitest cases. */
export function resetPublicMaintenanceStatusCache(): void {
  inflight = null;
  cached = null;
}

export function fetchPublicMaintenanceStatus(): Promise<PublicMaintenanceStatus> {
  const now = Date.now();
  if (cached && now - cached.at < CACHE_TTL_MS) {
    return Promise.resolve(cached.value);
  }
  if (inflight) return inflight;

  inflight = apiRequest<PublicMaintenanceStatus>("/maintenance/status")
    .then((value) => {
      cached = { at: Date.now(), value };
      return value;
    })
    .finally(() => {
      inflight = null;
    });

  return inflight;
}
