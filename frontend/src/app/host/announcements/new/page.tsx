"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { HostAnnouncementAIAssist } from "@/components/host/announcements/HostAnnouncementAIAssist";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, Input, Select, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { createAnnouncement, dispatchAnnouncementEmail, fetchSegments } from "@/lib/crm-api";
import { fetchMyEvents } from "@/lib/events-api";
import type { AudienceSegment } from "@/lib/types/crm";
import type { EventItem } from "@/lib/types/events";

function FormSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="space-y-4 border-b border-border pb-8 last:border-b-0 last:pb-0">
      <legend className="sr-only">{title}</legend>
      <div className="space-y-1">
        <h3 className="text-lg font-extrabold text-foreground">{title}</h3>
        {description ? (
          <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="space-y-4">{children}</div>
    </fieldset>
  );
}

export default function NewAnnouncementPage() {
  const router = useRouter();
  const [segments, setSegments] = useState<AudienceSegment[]>([]);
  const [title, setTitle] = useState("");
  const [bodyEmail, setBodyEmail] = useState("");
  const [bodyWhatsapp, setBodyWhatsapp] = useState("");
  const [channel, setChannel] = useState("both");
  const [segmentKey, setSegmentKey] = useState("followers");
  const [events, setEvents] = useState<EventItem[]>([]);
  const [contextEventId, setContextEventId] = useState("");
  const [aiNotes, setAiNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitAction, setSubmitAction] = useState<"draft" | "send" | null>(null);

  const canSendEmail = channel === "email" || channel === "both";

  useEffect(() => {
    let active = true;
    void fetchSegments()
      .then((rows) => {
        if (active) setSegments(rows);
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load segments");
        }
      });
    void fetchMyEvents()
      .then((rows) => {
        if (active) setEvents(rows.slice(0, 50));
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  async function handleCreate(sendEmail: boolean) {
    setError(null);
    setSubmitting(true);
    setSubmitAction(sendEmail ? "send" : "draft");
    try {
      const created = await createAnnouncement({
        title,
        body_email: bodyEmail,
        body_whatsapp: bodyWhatsapp || null,
        channel,
        segment_key: segmentKey,
      });
      if (sendEmail && canSendEmail) {
        const result = await dispatchAnnouncementEmail(created.id);
        const params = new URLSearchParams({
          id: created.id,
          emailed: String(result.emailed),
          skipped: String(result.skipped),
        });
        router.push(`/host/announcements?${params.toString()}`);
        return;
      }
      router.push(`/host/announcements?id=${created.id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : sendEmail
            ? "Could not create or send announcement"
            : "Could not create announcement",
      );
      setSubmitting(false);
      setSubmitAction(null);
    }
  }

  function onSubmitDraft(event: FormEvent) {
    event.preventDefault();
    void handleCreate(false);
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Audience"
        title="New announcement"
        description="Target a segment. Email only goes to marketing opt-in; WhatsApp is draft/export only."
        actions={
          <Link href="/host/announcements">
            <Button variant="ghost">Back to announcements</Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Could not create announcement">
            {error}
          </Alert>
        ) : null}

        <Card className="max-w-2xl">
          <form className="space-y-8" onSubmit={onSubmitDraft}>
            <FormSection title="Basics" description="Internal title for your broadcast history.">
              <Input
                label="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                hint="Not shown to recipients — for your records."
                required
              />
            </FormSection>

            <FormSection
              title="Audience & channel"
              description="Choose who receives this and how."
            >
              <Select
                label="Target segment"
                value={segmentKey}
                onChange={(e) => setSegmentKey(e.target.value)}
                hint="Recipients are resolved when the draft is created."
              >
                {segments.map((s) => (
                  <option key={s.id} value={s.segment_key}>
                    {s.name} ({s.member_count})
                    {s.segment_key === "superfans" || s.segment_key === "vault_subscribers"
                      ? " — placeholder"
                      : ""}
                  </option>
                ))}
              </Select>
              <Select
                label="Channel"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                hint="WhatsApp creates export copy only — no automated send."
              >
                <option value="email">Email</option>
                <option value="whatsapp">WhatsApp (export only)</option>
                <option value="both">Both</option>
              </Select>
            </FormSection>

            <FormSection
              title="Message content"
              description="Write channel-specific copy. Email requires at least 5 characters."
            >
              <HostAnnouncementAIAssist
                title={title}
                bodyEmail={bodyEmail}
                bodyWhatsapp={bodyWhatsapp}
                channel={channel}
                segmentKey={segmentKey}
                segmentLabel={
                  segments.find((s) => s.segment_key === segmentKey)?.name ??
                  segmentKey
                }
                eventId={contextEventId}
                hostNotes={aiNotes}
                onApply={(patch) => {
                  if (patch.title) setTitle(patch.title);
                  setBodyEmail(patch.bodyEmail);
                  if (patch.bodyWhatsapp !== undefined) {
                    setBodyWhatsapp(patch.bodyWhatsapp);
                  }
                }}
              />
              <Select
                label="Related event (optional, for AI context)"
                value={contextEventId}
                onChange={(e) => setContextEventId(e.target.value)}
                hint="Public event fields only — never recipient data."
              >
                <option value="">— None —</option>
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.title}
                  </option>
                ))}
              </Select>
              <Textarea
                label="Notes for AI (optional)"
                value={aiNotes}
                onChange={(e) => setAiNotes(e.target.value)}
                hint="Tone, promo angle, or reminders — not recipient details."
                className="min-h-[80px]"
              />
              <Textarea
                label="Email body"
                value={bodyEmail}
                onChange={(e) => setBodyEmail(e.target.value)}
                hint="Sent to marketing opt-in recipients when dispatched — wrapped in Pàdéyá branding with your host profile link."
                className="min-h-[140px]"
                required
                minLength={5}
              />
              <Textarea
                label="WhatsApp body (optional)"
                value={bodyWhatsapp}
                onChange={(e) => setBodyWhatsapp(e.target.value)}
                hint="Short copy for manual WhatsApp broadcast."
                className="min-h-[100px]"
                placeholder="Short copy for manual WhatsApp broadcast"
              />
            </FormSection>

            <div className="sticky bottom-0 -mx-5 flex flex-col gap-3 border-t border-border bg-card/95 px-5 py-4 backdrop-blur-sm sm:-mx-6 sm:flex-row sm:flex-wrap sm:items-center sm:px-6">
              {canSendEmail ? (
                <Button
                  type="button"
                  disabled={submitting}
                  className="w-full sm:order-2 sm:w-auto"
                  onClick={() => void handleCreate(true)}
                >
                  {submitting && submitAction === "send"
                    ? "Creating & sending…"
                    : "Create + send email"}
                </Button>
              ) : null}
              <Button
                type="submit"
                variant={canSendEmail ? "secondary" : "primary"}
                disabled={submitting}
                className="w-full sm:order-1 sm:w-auto"
              >
                {submitting && submitAction === "draft"
                  ? "Creating…"
                  : "Create draft + recipients"}
              </Button>
              {canSendEmail ? (
                <p className="text-xs text-muted-foreground sm:order-3 sm:basis-full">
                  Send uses marketing opt-in only. Fans who opt in after this
                  page still count when you dispatch.
                </p>
              ) : null}
            </div>
          </form>
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
