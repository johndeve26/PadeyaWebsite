"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { EventOpsNav } from "@/components/host/EventOpsNav";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Media,
  SectionHeader,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import {
  deleteMemoryPhoto,
  fetchHostMemory,
  moderateHostAttendeePhoto,
  patchMemoryPhoto,
  updateHostMemory,
  uploadHostMemoryPhoto,
} from "@/lib/memories-api";
import {
  EXTERNAL_GALLERY_LABELS,
  type EventMemory,
} from "@/lib/types/memories";

export default function HostEventMemoryPage() {
  const params = useParams<{ id: string }>();
  const eventId = params.id;
  const fileRef = useRef<HTMLInputElement>(null);
  const [memory, setMemory] = useState<EventMemory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [extUrl, setExtUrl] = useState("");
  const [extLabel, setExtLabel] = useState("other");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function reload() {
    const data = await fetchHostMemory(eventId);
    setMemory(data);
    setNote(data.host_recap_note || "");
    setExtUrl(data.external_gallery_url || "");
    setExtLabel(data.external_gallery_label || "other");
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await reload();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Memory unavailable");
        }
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId]);

  const hostCount =
    memory?.counts?.host_memory_count ??
    memory?.media.filter((m) => (m.uploader_role || "host") === "host").length ??
    0;
  const community =
    memory?.community_media?.length
      ? memory.community_media
      : memory?.media.filter((m) => m.uploader_role === "fan") ?? [];
  const hostPhotos =
    memory?.host_media?.length
      ? memory.host_media
      : memory?.media.filter((m) => (m.uploader_role || "host") === "host") ?? [];
  const publicPath =
    memory?.memories_path ||
    (memory ? `/events/${memory.event_slug}/memories` : "");

  async function onUpload(fileList: FileList | null) {
    if (!fileList?.length) return;
    const remaining = Math.max(0, 10 - hostCount);
    if (remaining <= 0) return;
    const files = Array.from(fileList).slice(0, remaining);
    setBusy(true);
    setError(null);
    track(TrackedAction.MEMORY_UPLOAD_STARTED, {
      targetEventId: eventId,
      count: files.length,
    });
    let uploaded = 0;
    let lastError: string | null = null;
    try {
      for (const file of files) {
        try {
          await uploadHostMemoryPhoto(eventId, file);
          uploaded += 1;
        } catch (err) {
          lastError =
            err instanceof ApiError ? err.detail : "Upload failed";
          break;
        }
      }
      if (uploaded > 0) {
        track(TrackedAction.MEMORY_UPLOAD_COMPLETED, {
          targetEventId: eventId,
          count: uploaded,
        });
        await reload();
      }
      if (lastError) {
        track(TrackedAction.MEMORY_UPLOAD_FAILED, { targetEventId: eventId });
        setError(
          uploaded > 0
            ? `Uploaded ${uploaded} of ${files.length}. ${lastError}`
            : lastError,
        );
      } else if (fileList.length > files.length) {
        setError(
          `Only ${remaining} slot${remaining === 1 ? "" : "s"} left — uploaded ${uploaded}.`,
        );
      }
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function saveSettings() {
    setBusy(true);
    setError(null);
    try {
      await updateHostMemory(eventId, {
        host_recap_note: note || null,
        external_gallery_url: extUrl || null,
        external_gallery_label: extUrl ? extLabel : null,
      });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        title="Event memories"
        description="Host album, attendee photos, and external gallery link."
      >
        <EventOpsNav eventId={eventId} eventStatus="completed" />

        {error ? (
          <Alert tone="danger" title="Error" className="mt-6">
            {error}
          </Alert>
        ) : null}

        {!memory ? (
          <EmptyState
            className="mt-8"
            title="Loading memories"
            description="Fetching album…"
          />
        ) : (
          <div className="mt-8 space-y-8">
            <div className="flex flex-wrap items-center gap-3">
              <Badge tone="info">
                Host {hostCount} / 10
              </Badge>
              <Badge tone="neutral">
                Attendees {memory.counts?.community_memory_count ?? community.length}
              </Badge>
              <Link href={publicPath} target="_blank">
                <Button variant="secondary" size="sm">
                  View public memories
                </Button>
              </Link>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={async () => {
                  const url = `${window.location.origin}${publicPath}`;
                  await navigator.clipboard.writeText(url);
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 2000);
                }}
              >
                {copied ? "Copied" : "Copy memories URL"}
              </Button>
            </div>

            <Card className="space-y-4 p-5">
              <SectionHeader
                title="Host memories"
                description="Select multiple photos at once — up to 10 optimized images. Set a cover for the album card."
              />
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                className="sr-only"
                disabled={busy || hostCount >= 10}
                onChange={(e) => void onUpload(e.target.files)}
              />
              <Button
                type="button"
                disabled={busy || hostCount >= 10}
                onClick={() => fileRef.current?.click()}
              >
                {busy ? "Uploading…" : "Upload photos"}
              </Button>
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {hostPhotos.map((photo) => (
                  <li key={photo.id} className="space-y-2">
                    <div className="relative aspect-square overflow-hidden rounded-xl bg-surface-muted">
                      <Media
                        src={photo.thumbnail_url || photo.url}
                        alt=""
                        fill
                        className="object-cover"
                      />
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={busy || photo.is_cover}
                        onClick={() =>
                          void patchMemoryPhoto(
                            eventId,
                            photo.id,
                            { is_cover: true },
                            true,
                          ).then(reload)
                        }
                      >
                        {photo.is_cover ? "Cover" : "Set cover"}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() =>
                          void deleteMemoryPhoto(eventId, photo.id, true).then(
                            reload,
                          )
                        }
                      >
                        Delete
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="space-y-4 p-5">
              <SectionHeader
                title="Attendee memories"
                description="Hide inappropriate photos. You cannot edit attendee captions."
              />
              {community.length === 0 ? (
                <p className="text-sm text-muted-foreground">No attendee photos yet.</p>
              ) : (
                <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {community.map((photo) => (
                    <li key={photo.id} className="space-y-2">
                      <div className="relative aspect-square overflow-hidden rounded-xl bg-surface-muted">
                        <Media
                          src={photo.thumbnail_url || photo.url}
                          alt=""
                          fill
                          className="object-cover"
                        />
                      </div>
                      <p className="truncate text-xs text-muted-foreground">
                        {photo.attribution || "Verified attendee"}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {photo.status === "hidden" ? (
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() =>
                              void moderateHostAttendeePhoto(eventId, photo.id, {
                                action: "restore",
                              }).then(reload)
                            }
                          >
                            Restore
                          </Button>
                        ) : (
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() =>
                              void moderateHostAttendeePhoto(eventId, photo.id, {
                                action: "hide",
                              }).then(reload)
                            }
                          >
                            Hide
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="space-y-4 p-5">
              <SectionHeader
                title="Recap & external gallery"
                description="Optional thank-you note and link to Instagram, Drive, or another gallery."
              />
              <label className="block text-sm font-semibold">
                Host recap
                <Textarea
                  className="mt-1"
                  rows={4}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </label>
              <label className="block text-sm font-semibold">
                External gallery type
                <Select
                  className="mt-1"
                  value={extLabel}
                  onChange={(e) => setExtLabel(e.target.value)}
                >
                  {EXTERNAL_GALLERY_LABELS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block text-sm font-semibold">
                External gallery URL
                <Input
                  className="mt-1"
                  type="url"
                  placeholder="https://"
                  value={extUrl}
                  onChange={(e) => setExtUrl(e.target.value)}
                />
              </label>
              <Button type="button" disabled={busy} onClick={() => void saveSettings()}>
                Save settings
              </Button>
            </Card>
          </div>
        )}
      </DashboardShell>
    </RequireHost>
  );
}
