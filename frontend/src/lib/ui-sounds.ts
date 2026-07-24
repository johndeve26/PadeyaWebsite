const PREFS_KEY = "padeya.ui-sounds.v1";

export type UiSoundPreferences = {
  notifications: boolean;
  scan: boolean;
};

const DEFAULT_PREFS: UiSoundPreferences = {
  notifications: true,
  scan: true,
};

export function readUiSoundPreferences(): UiSoundPreferences {
  if (typeof window === "undefined") return { ...DEFAULT_PREFS };
  try {
    const raw = window.localStorage.getItem(PREFS_KEY);
    if (!raw) return { ...DEFAULT_PREFS };
    const parsed = JSON.parse(raw) as Partial<UiSoundPreferences>;
    return {
      notifications: parsed.notifications !== false,
      scan: parsed.scan !== false,
    };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function writeUiSoundPreferences(
  patch: Partial<UiSoundPreferences>,
): UiSoundPreferences {
  const merged = { ...readUiSoundPreferences(), ...patch };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(PREFS_KEY, JSON.stringify(merged));
  }
  return merged;
}

type ToneStep = {
  freq: number;
  ms: number;
  gap?: number;
  type?: OscillatorType;
  volume?: number;
};

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const AnyWindow = window as Window &
    typeof globalThis & { webkitAudioContext?: typeof AudioContext };
  const Ctx = AnyWindow.AudioContext ?? AnyWindow.webkitAudioContext;
  if (!Ctx) return null;
  if (!audioCtx) audioCtx = new Ctx();
  return audioCtx;
}

export async function unlockUiSounds(): Promise<void> {
  const ctx = getAudioContext();
  if (!ctx) return;
  if (ctx.state === "suspended") {
    await ctx.resume();
  }
}

function playToneSequence(steps: ToneStep[]): void {
  const ctx = getAudioContext();
  if (!ctx) return;

  const run = () => {
    if (ctx.state === "suspended") return;
    let t = ctx.currentTime;
    for (const step of steps) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = step.type ?? "sine";
      osc.frequency.value = step.freq;
      const vol = step.volume ?? 0.14;
      const dur = step.ms / 1000;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(Math.max(vol, 0.0001), t + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + dur + 0.04);
      t += dur + (step.gap ?? 0) / 1000;
    }
  };

  if (ctx.state === "running") {
    run();
    return;
  }
  void unlockUiSounds().then(run);
}

/** Short chime when an in-app notification toast appears. */
export function playInAppNotificationSound(): void {
  if (!readUiSoundPreferences().notifications) return;
  playToneSequence([
    { freq: 880, ms: 110, gap: 45 },
    { freq: 1175, ms: 130 },
  ]);
}

export type ScanSoundKind = "success" | "warning" | "error" | "info";

export function scanOutcomeToSoundKind(outcome: string): ScanSoundKind {
  if (outcome === "success" || outcome === "valid") return "success";
  if (outcome === "duplicate" || outcome === "queued") return "warning";
  if (outcome === "invalid") return "error";
  return "info";
}

/** Door scanner feedback — distinct tones per outcome. */
export function playCheckInScanSound(outcome: string): void {
  if (!readUiSoundPreferences().scan) return;
  const kind = scanOutcomeToSoundKind(outcome);
  switch (kind) {
    case "success":
      playToneSequence([{ freq: 1046, ms: 95 }]);
      break;
    case "warning":
      playToneSequence([
        { freq: 659, ms: 85, gap: 55 },
        { freq: 659, ms: 85 },
      ]);
      break;
    case "error":
      playToneSequence([{ freq: 220, ms: 170, type: "square", volume: 0.07 }]);
      break;
    default:
      playToneSequence([{ freq: 523, ms: 75 }]);
      break;
  }
}
