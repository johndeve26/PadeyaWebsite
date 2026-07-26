"use client";

import { useEffect, useRef, useState } from "react";

import { Alert, Button } from "@/components/ui";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import {
  fetchMemoryEligibility,
  uploadFanMemoryPhoto,
} from "@/lib/memories-api";
import type { MemoryEligibility } from "@/lib/types/memories";

export function FanMemoryUploadCard({
  eventId,
  eventSlug,
  eventTitle,
}: {
  eventId: string;
  eventSlug: string;
  eventTitle: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [eligibility, setEligibility] = useState<MemoryEligibility | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchMemoryEligibility(eventSlug)
      .then((data) => {
        if (active) setEligibility(data);
      })
      .catch(() => {
        if (active) setEligibility(null);
      });
    return () => {
      active = false;
    };
  }, [eventSlug]);

  if (!eligibility?.authenticated) return null;
  if (eligibility.role === "host") return null;
  if (!eligibility.ticket_verified || !eligibility.event_started) return null;

  async function onFile(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    track(TrackedAction.MEMORY_UPLOAD_STARTED, { targetEventId: eventId });
    try {
      await uploadFanMemoryPhoto(eventId, file);
      track(TrackedAction.MEMORY_UPLOAD_COMPLETED, { targetEventId: eventId });
      setMessage("Photo added to community memories.");
      const next = await fetchMemoryEligibility(eventSlug);
      setEligibility(next);
    } catch (err) {
      track(TrackedAction.MEMORY_UPLOAD_FAILED, { targetEventId: eventId });
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <p className="text-sm font-extrabold uppercase tracking-wide text-[color:var(--brand-green-hover)]">
        You were there ✓
      </p>
      <h3 className="mt-2 text-lg font-extrabold tracking-tight text-foreground">
        Add your memories
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Share up to {eligibility.limit} photos from {eventTitle}.{" "}
        {eligibility.used}/{eligibility.limit} used.
      </p>
      {message ? (
        <Alert tone="success" title="Uploaded" className="mt-4">
          {message}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Upload failed" className="mt-4">
          {error}
        </Alert>
      ) : null}
      <div className="mt-4">
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          disabled={busy || !eligibility.can_upload}
          onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
        />
        <Button
          type="button"
          disabled={busy || !eligibility.can_upload}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? "Uploading…" : "Upload photo"}
        </Button>
      </div>
    </div>
  );
}
