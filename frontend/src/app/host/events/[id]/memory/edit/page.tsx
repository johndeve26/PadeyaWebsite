"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  Media,
  SectionHeader,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  addMemoryMedia,
  deleteMemoryMedia,
  fetchHostMemory,
  updateHostMemory,
} from "@/lib/memories-api";
import type { EventMemory } from "@/lib/types/memories";

export default function HostEventMemoryEditPage() {
  const params = useParams<{ id: string }>();
  const [memory, setMemory] = useState<EventMemory | null>(null);
  const [note, setNote] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [mediaLabel, setMediaLabel] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchHostMemory(params.id);
        if (active) {
          setMemory(data);
          setNote(data.host_recap_note || "");
        }
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Memory unavailable");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onSaveNote() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateHostMemory(params.id, {
        host_recap_note: note.trim() || null,
      });
      setMemory(updated);
      setMessage("Recap note saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onAddMedia() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await addMemoryMedia(params.id, {
        url: mediaUrl,
        media_type: "image",
        label: mediaLabel.trim() || null,
      });
      setMemory(updated);
      setMediaUrl("");
      setMediaLabel("");
      setMessage("Media added.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteMedia(mediaId: string) {
    setBusy(true);
    setError(null);
    try {
      const updated = await deleteMemoryMedia(params.id, mediaId);
      setMemory(updated);
      setMessage("Media removed.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Event Memory"
        title="Edit memory"
        description="Update the thank-you note and gallery for this completed event."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={`/host/events/${params.id}/memory`}>
              <Button size="sm" variant="ghost">
                Back to memory
              </Button>
            </Link>
            {memory?.status === "published" ? (
              <Link href={memory.share_path}>
                <Button size="sm" variant="secondary">
                  View public page
                </Button>
              </Link>
            ) : null}
          </div>
        }
      >
        {message ? (
          <Alert tone="success" title="Saved">
            {message}
          </Alert>
        ) : null}
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        {memory ? (
          <div className="flex flex-wrap gap-2">
            <Badge tone={memory.status === "published" ? "success" : "neutral"}>
              {memory.status}
            </Badge>
            <Badge tone="neutral">{memory.media.length} gallery items</Badge>
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="space-y-4">
            <SectionHeader
              title="Host thank-you note"
              description="Shown on the public memory page after the event."
            />
            <Textarea
              label="Recap note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={8}
              placeholder="Thank you to everyone who came through…"
            />
            <Button disabled={busy} onClick={() => void onSaveNote()}>
              {busy ? "Saving…" : "Save note"}
            </Button>
          </Card>

          <Card className="space-y-4">
            <SectionHeader
              title="Add gallery media"
              description="Upload an image or paste a URL for this memory gallery."
            />
            <ImageUrlOrUploadField
              label="Gallery image"
              value={mediaUrl}
              onChange={setMediaUrl}
              eventId={params.id}
              mediaType="gallery"
              previewClassName="h-16 w-24"
            />
            <Input
              label="Label (optional)"
              value={mediaLabel}
              onChange={(e) => setMediaLabel(e.target.value)}
              placeholder="Stage shot, crowd moment…"
            />
            <Button
              disabled={busy || !mediaUrl.trim()}
              variant="secondary"
              onClick={() => void onAddMedia()}
            >
              Add media
            </Button>
          </Card>
        </div>

        {memory && memory.media.length > 0 ? (
          <section className="mt-8 space-y-4">
            <SectionHeader title="Current gallery" />
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {memory.media.map((m) => (
                <Card key={m.id} padded={false} className="overflow-hidden">
                  <div className="relative aspect-[4/3] bg-surface-dark">
                    <Media
                      src={m.url}
                      alt={m.label ?? m.media_type}
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <div className="flex items-center justify-between gap-2 p-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">
                        {m.label || m.media_type}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">{m.url}</p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => void onDeleteMedia(m.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
