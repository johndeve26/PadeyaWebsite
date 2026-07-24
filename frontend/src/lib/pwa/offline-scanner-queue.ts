/**
 * Offline scanner queue — stores scans locally and syncs via Phase 17 offline sync API.
 */

import { syncOfflineScans } from "@/lib/advanced-tickets-api";
import type { OfflineSyncResult } from "@/lib/types/advanced-tickets";

const QUEUE_PREFIX = "padeya.scanner.queue.v1.";

export type QueuedScan = {
  client_scan_id: string;
  qr_payload?: string;
  public_code?: string;
  scanned_at: string;
};

function key(eventId: string): string {
  return `${QUEUE_PREFIX}${eventId}`;
}

export function loadScannerQueue(eventId: string): QueuedScan[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(key(eventId));
    return raw ? (JSON.parse(raw) as QueuedScan[]) : [];
  } catch {
    return [];
  }
}

export function saveScannerQueue(eventId: string, scans: QueuedScan[]): void {
  localStorage.setItem(key(eventId), JSON.stringify(scans));
}

export function enqueueScannerScan(
  eventId: string,
  scan: Omit<QueuedScan, "client_scan_id" | "scanned_at"> & {
    client_scan_id?: string;
  },
): QueuedScan[] {
  const next: QueuedScan[] = [
    ...loadScannerQueue(eventId),
    {
      client_scan_id:
        scan.client_scan_id ??
        `q-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      qr_payload: scan.qr_payload,
      public_code: scan.public_code,
      scanned_at: new Date().toISOString(),
    },
  ];
  saveScannerQueue(eventId, next);
  return next;
}

export async function flushScannerQueue(
  eventId: string,
  deviceLabel = "Mobile offline scanner",
): Promise<OfflineSyncResult | null> {
  const scans = loadScannerQueue(eventId);
  if (scans.length === 0) return null;

  const result = await syncOfflineScans({
    event_id: eventId,
    client_batch_id: `pwa-${eventId.slice(0, 8)}-${scans[0].client_scan_id}`,
    device_label: deviceLabel,
    scans: scans.map((s) => ({
      client_scan_id: s.client_scan_id,
      qr_payload: s.qr_payload,
      public_code: s.public_code,
      scanned_at: s.scanned_at,
    })),
  });
  saveScannerQueue(eventId, []);
  return result;
}

export function isBrowserOnline(): boolean {
  if (typeof navigator === "undefined") return true;
  return navigator.onLine;
}
