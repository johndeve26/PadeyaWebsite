"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { CheckInAttendeesPanel } from "@/components/checkin/CheckInAttendeesPanel";
import { CheckInCompactHeader } from "@/components/checkin/CheckInCompactHeader";
import { CheckInDoorStatsPanel } from "@/components/checkin/CheckInDoorStatsPanel";
import { CheckInOfflinePanel } from "@/components/checkin/CheckInOfflinePanel";
import { CheckInTabNav, type CheckInTab } from "@/components/checkin/CheckInTabNav";
import { RecentScansStrip } from "@/components/checkin/RecentScansStrip";
import { ScanResultOverlay } from "@/components/checkin/ScanResultOverlay";
import { toRecentScan, type RecentScanRow } from "@/components/checkin/scan-result-utils";
import { useAuth } from "@/components/auth/AuthProvider";
import { rememberScannerEvent } from "@/lib/host-scanner-entry";
import { Alert, Button, Drawer, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  scanTicket,
  startScannerSession,
  type ScanResult,
  type ScannerSession,
} from "@/lib/checkin-api";
import { cn } from "@/lib/cn";
import {
  enqueueScannerScan,
  flushScannerQueue,
  isBrowserOnline,
  loadScannerQueue,
} from "@/lib/pwa/offline-scanner-queue";

const QrScanner = dynamic(
  () => import("@/components/checkin/QrScanner").then((m) => m.QrScanner),
  {
    ssr: false,
    loading: () => (
      <div
        className="flex min-h-[240px] items-center justify-center rounded-[var(--radius-lg)] bg-surface-inset text-sm text-muted-foreground"
        aria-busy
      >
        Starting camera…
      </div>
    ),
  },
);
import { useOnlineStatus } from "@/lib/pwa/use-online-status";
import { playCheckInScanSound } from "@/lib/ui-sounds";

/** Keeps camera stream alive while visually hidden (avoid display:none or zero size). */
const SCANNER_OFFSCREEN =
  "pointer-events-none fixed left-4 top-24 z-0 h-[min(52vh,400px)] w-[min(100vw-2rem,28rem)] -translate-x-[120vw] opacity-0";

export function CheckInWorkspace({
  eventId,
  eventTitle,
  variant = "host",
}: {
  eventId: string;
  eventTitle?: string;
  variant?: "host" | "staff";
}) {
  const { user } = useAuth();
  const online = useOnlineStatus();
  const [tab, setTab] = useState<CheckInTab>("scanner");
  const [session, setSession] = useState<ScannerSession | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [recent, setRecent] = useState<RecentScanRow[]>([]);
  const [manualCode, setManualCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [userPaused, setUserPaused] = useState(false);
  const [processingPause, setProcessingPause] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [queued, setQueued] = useState(() => loadScannerQueue(eventId).length);
  const [syncNote, setSyncNote] = useState<string | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [scanCount, setScanCount] = useState(0);
  const [codeDrawerOpen, setCodeDrawerOpen] = useState(false);

  const hostBase = `/host/events/${eventId}`;
  const attendeesHref = variant === "host" ? `${hostBase}/attendees` : undefined;

  useEffect(() => {
    rememberScannerEvent(eventId);
  }, [eventId]);

  useEffect(() => {
    let active = true;
    if (!online) return;
    void (async () => {
      try {
        const started = await startScannerSession({
          event_id: eventId,
          device_label:
            typeof navigator !== "undefined"
              ? navigator.userAgent.slice(0, 80)
              : "web",
        });
        if (active) setSession(started);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Unable to start scanner session",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [eventId, online]);

  const pushRecent = useCallback((scan: ScanResult) => {
    setRecent((prev) => [toRecentScan(scan), ...prev].slice(0, 5));
  }, []);

  const handlePayload = useCallback(
    async (payload: { qr_payload?: string; public_code?: string }) => {
      setBusy(true);
      setProcessingPause(true);
      setError(null);
      setSyncNote(null);
      try {
        if (!isBrowserOnline()) {
          const next = enqueueScannerScan(eventId, payload);
          setQueued(next.length);
          const queuedResult = {
            outcome: "queued",
            message: "Offline — scan queued. Sync when you’re back online.",
            ticket: {
              ticket_id: null,
              public_code: payload.public_code ?? null,
              status: null,
              holder_name: null,
              holder_email: null,
              ticket_type_name: null,
              checked_in_at: null,
            },
            check_in_id: null,
            checked_in_at: null,
            scanner_name: user?.full_name ?? "Offline",
          } as ScanResult;
          setResult(queuedResult);
          pushRecent(queuedResult);
          playCheckInScanSound(queuedResult.outcome);
          setScanCount((n) => n + 1);
          return;
        }

        const scan = await scanTicket({
          event_id: eventId,
          session_id: session?.id,
          ...payload,
        });
        setResult(scan);
        pushRecent(scan);
        playCheckInScanSound(scan.outcome);
        setScanCount((n) => n + 1);
        if (scan.outcome === "success" || scan.outcome === "valid") {
          setManualCode("");
          setCodeDrawerOpen(false);
        }
      } catch (err) {
        if (!isBrowserOnline() || err instanceof TypeError) {
          const next = enqueueScannerScan(eventId, payload);
          setQueued(next.length);
          setSyncNote("Network error — scan queued for offline sync.");
        } else {
          setError(err instanceof ApiError ? err.detail : "Scan failed");
        }
      } finally {
        setBusy(false);
        window.setTimeout(() => setProcessingPause(false), 400);
      }
    },
    [eventId, pushRecent, session?.id, user?.full_name],
  );

  async function onManualSubmit(event: FormEvent) {
    event.preventDefault();
    const code = manualCode.trim();
    if (!code) return;
    await handlePayload({ public_code: code });
  }

  async function onFlushQueue() {
    setBusy(true);
    setError(null);
    try {
      const body = await flushScannerQueue(eventId);
      setQueued(0);
      setLastSyncAt(new Date().toISOString());
      if (body) {
        setSyncNote(
          `Synced: ${body.accepted_count} accepted, ${body.conflict_count} conflicts, ${body.invalid_count} invalid.`,
        );
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  const scannerLine = online
    ? session
      ? `${session.scanner_name ?? user?.full_name ?? "Scanner"} · session active`
      : "Starting session…"
    : "Offline — scans queue locally";

  const scannerPaused = busy || processingPause || userPaused;

  const scannerColumn = (
    <div className="space-y-3">
      {!online ? (
        <Alert tone="warning" title="Offline">
          Scans will be saved and synced when connection returns.
        </Alert>
      ) : null}
      {queued > 0 && online ? (
        <Alert
          tone="warning"
          title={`${queued} offline scan(s) waiting`}
          action={
            <Button size="sm" disabled={busy} onClick={() => void onFlushQueue()}>
              Sync now
            </Button>
          }
        >
          Conflicts are reported by the server when syncing.
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Scan error">
          {error}
        </Alert>
      ) : null}
      {syncNote ? (
        <Alert tone="info" title="Sync update">
          {syncNote}
        </Alert>
      ) : null}

      {result ? (
        <ScanResultOverlay
          result={result}
          queuedCount={queued}
          onContinue={() => setResult(null)}
          onManualSearch={() => {
            setResult(null);
            setTab("attendees");
          }}
          onViewDetails={() => {
            setResult(null);
            setTab("attendees");
          }}
        />
      ) : null}

      <div
        className={cn(result && SCANNER_OFFSCREEN)}
        aria-hidden={Boolean(result)}
      >
        <QrScanner
          paused={scannerPaused || Boolean(result)}
          userPaused={userPaused}
          onTogglePause={() => setUserPaused((v) => !v)}
          onEnterCode={() => setCodeDrawerOpen(true)}
          onSearchGuests={() => setTab("attendees")}
          onCameraReady={setCameraReady}
          onScan={(value) => {
            void handlePayload({ qr_payload: value });
          }}
        />
      </div>

      <RecentScansStrip rows={recent} attendeesHref={attendeesHref} />
    </div>
  );

  return (
    <div className="mx-auto min-w-0 max-w-5xl space-y-3 pb-8">
      <CheckInCompactHeader
        eventTitle={eventTitle}
        scannerLine={scannerLine}
        online={online}
        cameraReady={cameraReady}
        showCameraStatus={tab === "scanner"}
        queued={queued}
        scanCount={scanCount}
      />

      <CheckInTabNav active={tab} onSelect={setTab} />

      <div
        className={cn(tab !== "scanner" && SCANNER_OFFSCREEN)}
        aria-hidden={tab !== "scanner"}
      >
        <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,340px)] lg:items-start lg:gap-6">
          <div>{scannerColumn}</div>
          <aside className="hidden space-y-3 lg:block">
            <CheckInDoorStatsPanel
              eventId={eventId}
              scanCount={scanCount}
              queued={queued}
              lastScan={recent[0] ?? null}
            />
          </aside>
        </div>
      </div>

      {tab === "attendees" ? (
        <CheckInAttendeesPanel
          eventId={eventId}
          online={online}
          busy={busy}
          onCheckIn={(code) => void handlePayload({ public_code: code })}
        />
      ) : null}

      {tab === "stats" ? (
        <CheckInDoorStatsPanel
          eventId={eventId}
          scanCount={scanCount}
          queued={queued}
          lastScan={recent[0] ?? null}
        />
      ) : null}

      {tab === "offline" ? (
        <CheckInOfflinePanel
          eventId={eventId}
          variant={variant}
          online={online}
          queued={queued}
          lastSyncAt={lastSyncAt}
          busy={busy}
          onSync={() => void onFlushQueue()}
        />
      ) : null}

      <Drawer
        open={codeDrawerOpen}
        onClose={() => setCodeDrawerOpen(false)}
        title="Enter ticket code"
        description="Type a public ticket code (PDY-…) or paste a short code from the guest’s pass."
      >
        <form className="space-y-4" onSubmit={onManualSubmit}>
          <Input
            label="Ticket or order reference"
            value={manualCode}
            onChange={(e) => setManualCode(e.target.value)}
            placeholder="PDY-…"
            autoComplete="off"
            inputMode="text"
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={busy} className="min-h-11 flex-1">
              Check in
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setManualCode("")}
            >
              Clear
            </Button>
          </div>
        </form>
      </Drawer>
    </div>
  );
}
