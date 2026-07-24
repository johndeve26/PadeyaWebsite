"use client";

import { Html5Qrcode, type CameraDevice } from "html5-qrcode";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

const SCAN_CONFIG = { fps: 10, aspectRatio: 1.333, disableFlip: false } as const;

async function safeStopScanner(scanner: Html5Qrcode | null | undefined): Promise<void> {
  if (!scanner?.isScanning) return;
  try {
    await scanner.stop();
  } catch {
    // html5-qrcode throws if already stopped — ignore.
  }
}

export type QrScannerProps = {
  onScan: (value: string) => void;
  paused?: boolean;
  userPaused?: boolean;
  onTogglePause?: () => void;
  onEnterCode?: () => void;
  onSearchGuests?: () => void;
  onCameraReady?: (ready: boolean) => void;
  readerId?: string;
  className?: string;
};

export function QrScanner({
  onScan,
  paused = false,
  userPaused = false,
  onTogglePause,
  onEnterCode,
  onSearchGuests,
  onCameraReady,
  readerId = "padeya-qr-reader",
  className,
}: QrScannerProps) {
  const onScanRef = useRef(onScan);
  const onCameraReadyRef = useRef(onCameraReady);
  const pausedRef = useRef(paused || userPaused);
  const lastScan = useRef<string>("");
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const videoTrackRef = useRef<MediaStreamTrack | null>(null);
  const camerasRef = useRef<CameraDevice[]>([]);
  const cameraIndexRef = useRef(0);
  const facingRef = useRef<"environment" | "user">("environment");
  const mountIdRef = useRef(0);
  const startLockRef = useRef<Promise<void>>(Promise.resolve());

  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const [torchSupported, setTorchSupported] = useState(false);
  const [starting, setStarting] = useState(true);
  const [flipBusy, setFlipBusy] = useState(false);

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  useEffect(() => {
    onCameraReadyRef.current = onCameraReady;
  }, [onCameraReady]);

  useEffect(() => {
    pausedRef.current = paused || userPaused;
  }, [paused, userPaused]);

  function bindVideoTrack() {
    const el = document.getElementById(readerId);
    const video = el?.querySelector("video");
    const track =
      video?.srcObject instanceof MediaStream ? video.srcObject.getVideoTracks()[0] : null;
    videoTrackRef.current = track ?? null;
    if (track && "getCapabilities" in track) {
      const caps = track.getCapabilities?.() as { torch?: boolean } | undefined;
      setTorchSupported(Boolean(caps?.torch));
    }
  }

  async function startWithCameraConfig(
    cameraIdOrConfig: string | { facingMode: "user" | "environment" },
  ) {
    const run = async () => {
      const scanner = scannerRef.current ?? new Html5Qrcode(readerId);
      scannerRef.current = scanner;
      await safeStopScanner(scanner);

      await scanner.start(
        cameraIdOrConfig,
        SCAN_CONFIG,
        (decoded) => {
          if (pausedRef.current) return;
          if (decoded === lastScan.current) return;
          lastScan.current = decoded;
          onScanRef.current(decoded);
          window.setTimeout(() => {
            if (lastScan.current === decoded) lastScan.current = "";
          }, 2500);
        },
        () => undefined,
      );
      setRunning(true);
      setStarting(false);
      setError(null);
      onCameraReadyRef.current?.(true);
      window.setTimeout(() => bindVideoTrack(), 300);
    };

    startLockRef.current = startLockRef.current.then(run, run);
    try {
      await startLockRef.current;
    } catch (err) {
      setRunning(false);
      setStarting(false);
      const detail =
        typeof err === "string"
          ? err
          : err instanceof Error
            ? err.message
            : "Could not access the camera.";
      throw new Error(detail);
    }
  }

  async function requestCameraAccess(): Promise<void> {
    setStarting(true);
    setError(null);
    try {
      if (navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        for (const track of stream.getTracks()) {
          track.stop();
        }
      }
      await startWithCameraConfig({ facingMode: "environment" });
      try {
        const devices = await Html5Qrcode.getCameras();
        camerasRef.current = devices;
        const backIdx = devices.findIndex((d) => /back|rear|environment/i.test(d.label));
        cameraIndexRef.current = backIdx >= 0 ? backIdx : 0;
      } catch {
        // optional
      }
    } catch (err) {
      setRunning(false);
      setStarting(false);
      const msg =
        err instanceof Error ? err.message : "Could not access the camera.";
      if (/denied|permission|not allowed/i.test(msg)) {
        setError(
          "Camera permission is blocked. Allow camera for this site in browser settings, then tap Retry.",
        );
      } else {
        setError(`${msg} Tap Retry to try again, or use Enter code.`);
      }
      onCameraReadyRef.current?.(false);
    }
  }

  useEffect(() => {
    if (typeof window !== "undefined" && !window.isSecureContext) {
      setError(
        "Camera needs a secure connection (HTTPS). Use manual code or guest search instead.",
      );
      setStarting(false);
      onCameraReadyRef.current?.(false);
      return;
    }

    const mountId = ++mountIdRef.current;
    let cancelled = false;

    const scanner = new Html5Qrcode(readerId);
    scannerRef.current = scanner;

    void (async () => {
      await new Promise((r) => requestAnimationFrame(() => r(undefined)));
      if (cancelled || mountId !== mountIdRef.current) return;
      await requestCameraAccess();
      if (cancelled || mountId !== mountIdRef.current) return;
    })();

    return () => {
      cancelled = true;
      setRunning(false);
      setStarting(true);
      void safeStopScanner(scanner);
      onCameraReadyRef.current?.(false);
    };
  }, [readerId]);

  async function ensureRunning() {
    if (scannerRef.current?.isScanning) return true;
    try {
      await requestCameraAccess();
      return Boolean(scannerRef.current?.isScanning);
    } catch {
      return false;
    }
  }

  async function switchCamera() {
    if (flipBusy) return;
    setFlipBusy(true);
    setTorchOn(false);
    try {
      const ok = await ensureRunning();
      const scanner = scannerRef.current;
      if (!ok || !scanner?.isScanning) return;

      const devices = camerasRef.current;

      if (devices.length >= 2) {
        const next = (cameraIndexRef.current + 1) % devices.length;
        const deviceId = devices[next]?.id;
        if (deviceId) {
          try {
            await scanner.applyVideoConstraints({ deviceId: { exact: deviceId } });
            cameraIndexRef.current = next;
            bindVideoTrack();
            return;
          } catch {
            await safeStopScanner(scanner);
            await startWithCameraConfig(deviceId);
            cameraIndexRef.current = next;
            return;
          }
        }
      }

      const nextFacing = facingRef.current === "environment" ? "user" : "environment";
      try {
        await scanner.applyVideoConstraints({ facingMode: nextFacing });
        facingRef.current = nextFacing;
        bindVideoTrack();
      } catch {
        await safeStopScanner(scanner);
        facingRef.current = nextFacing;
        await startWithCameraConfig({ facingMode: nextFacing });
      }
    } catch {
      setError("Could not switch camera.");
    } finally {
      setFlipBusy(false);
    }
  }

  async function toggleTorch() {
    const scanner = scannerRef.current;
    const track = videoTrackRef.current;
    if (!track || !torchSupported) return;
    try {
      const next = !torchOn;
      if (scanner?.isScanning) {
        await scanner.applyVideoConstraints({
          advanced: [{ torch: next } as MediaTrackConstraintSet],
        });
      } else {
        await track.applyConstraints({
          advanced: [{ torch: next } as MediaTrackConstraintSet],
        });
      }
      setTorchOn(next);
    } catch {
      setTorchSupported(false);
    }
  }

  const effectivePaused = paused || userPaused;
  const showStartingLayer = (starting || !running) && !error;

  function ScanBarButton({
    children,
    onClick,
    disabled,
    accent,
  }: {
    children: ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    accent?: boolean;
  }) {
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className={cn(
          "relative z-20 min-h-10 min-w-[4.5rem] flex-1 rounded-[var(--radius-sm)] px-2 text-[11px] font-bold leading-tight sm:text-xs",
          accent
            ? "bg-accent text-accent-foreground shadow-sm"
            : "border border-paper/40 bg-paper/15 text-paper backdrop-blur-sm hover:bg-paper/25",
          disabled && "opacity-40",
        )}
      >
        {children}
      </button>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div
        className={cn(
          "relative isolate mx-auto w-full max-w-md overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink",
          "aspect-[4/5] max-h-[min(52vh,400px)]",
        )}
      >
        <div
          id={readerId}
          className={cn(
            "absolute inset-0 z-0",
            "[&_img]:hidden",
            "[&_video]:h-full [&_video]:w-full [&_video]:object-cover",
            "[&_#qr-shaded-region]:hidden",
          )}
        />

        {showStartingLayer ? (
          <div className="pointer-events-none absolute inset-0 z-[1] flex flex-col items-center justify-center gap-2 bg-ink px-4 text-center">
            <p className="text-sm font-bold text-paper">Starting camera…</p>
            <p className="text-xs text-subtle-foreground">Allow camera once for this session</p>
          </div>
        ) : null}

        {running && !error ? (
          <>
            <div className="pointer-events-none absolute inset-x-0 top-0 z-[2] flex items-start justify-between gap-2 p-3">
              <span className="rounded-full bg-ink/70 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-paper">
                {effectivePaused ? "Paused" : flipBusy ? "Switching…" : "Camera live"}
              </span>
              {torchSupported ? (
                <button
                  type="button"
                  className="pointer-events-auto rounded-full bg-ink/70 px-2 py-1 text-[10px] font-bold text-accent"
                  onClick={() => void toggleTorch()}
                >
                  {torchOn ? "Flash off" : "Flash on"}
                </button>
              ) : null}
            </div>

            {!effectivePaused ? (
              <div className="pointer-events-none absolute inset-0 z-[2] flex items-center justify-center p-10 pb-16">
                <div className="relative aspect-square w-[min(70%,240px)]">
                  <span className="absolute left-0 top-0 h-7 w-7 border-l-[3px] border-t-[3px] border-accent" />
                  <span className="absolute right-0 top-0 h-7 w-7 border-r-[3px] border-t-[3px] border-accent" />
                  <span className="absolute bottom-0 left-0 h-7 w-7 border-b-[3px] border-l-[3px] border-accent" />
                  <span className="absolute bottom-0 right-0 h-7 w-7 border-b-[3px] border-r-[3px] border-accent" />
                  <span className="absolute inset-x-4 top-1/2 h-px animate-pulse bg-accent/50" />
                </div>
              </div>
            ) : null}

            {!effectivePaused && !starting ? (
              <p className="pointer-events-none absolute inset-x-0 bottom-[4.25rem] z-[2] text-center text-[11px] font-semibold text-paper/90 drop-shadow">
                Aim a ticket QR in the frame
              </p>
            ) : null}
          </>
        ) : null}

        {error ? (
          <div className="absolute inset-0 z-[5] flex flex-col items-center justify-center gap-3 bg-ink/95 px-4 pb-20 text-center">
            <p className="text-sm font-semibold text-paper">{error}</p>
            <ScanBarButton accent onClick={() => void requestCameraAccess()}>
              Retry camera
            </ScanBarButton>
          </div>
        ) : null}

        <div className="absolute inset-x-0 bottom-0 z-10 grid grid-cols-2 gap-2 bg-gradient-to-t from-ink via-ink/95 to-transparent p-3 pt-10 sm:grid-cols-4">
          {onTogglePause ? (
            <ScanBarButton onClick={onTogglePause} disabled={flipBusy}>
              {userPaused ? "Resume" : "Pause"}
            </ScanBarButton>
          ) : null}
          <ScanBarButton disabled={flipBusy} onClick={() => void switchCamera()}>
            Flip cam
          </ScanBarButton>
          {onEnterCode ? (
            <ScanBarButton accent onClick={onEnterCode}>
              Enter code
            </ScanBarButton>
          ) : null}
          {onSearchGuests ? (
            <ScanBarButton onClick={onSearchGuests}>Search</ScanBarButton>
          ) : null}
        </div>
      </div>
    </div>
  );
}
