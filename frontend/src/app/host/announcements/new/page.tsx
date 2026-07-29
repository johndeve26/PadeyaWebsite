"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { RequireHost } from "@/components/hosts/RequireHost";
import { HostAnnouncementAIAssist } from "@/components/host/announcements/HostAnnouncementAIAssist";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, Input, Select, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { errorDetail } from "@/lib/api-timeouts";
import {
  hasImpersonationScope,
  hasUnrestrictedImpersonation,
  IMPERSONATION_SCOPE_HOST_EVENTS,
  packLabel,
} from "@/lib/auth/impersonation-scopes";
import { createAnnouncement, dispatchAnnouncementEmail, fetchSegments } from "@/lib/crm-api";
import { fetchMyEvents } from "@/lib/events-api";
import type { AudienceSegment } from "@/lib/types/crm";
import type { EventItem } from "@/lib/types/events";

const NAME_TOKEN = "{{name}}";
const IMPERSONATION_BLOCKED =
  "This action is disabled during admin impersonation.";

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

function insertNameToken(text: string): string {
  if (text.includes(NAME_TOKEN)) return text;
  const trimmed = text.trim();
  if (!trimmed) return `Hi ${NAME_TOKEN},\n\n`;
  return `Hi ${NAME_TOKEN},\n\n${trimmed}`;
}

function announcementErrorTitle(message: string): string {
  if (message.startsWith("Draft saved")) {
    return "Announcement saved — email not sent";
  }
  if (message.includes("impersonation")) {
    return "Blocked during impersonation";
  }
  return "Could not create announcement";
}

export default function NewAnnouncementPage() {
  const router = useRouter();
  const { isImpersonating, impersonation } = useAuth();
  const [segments, setSegments] = useState<AudienceSegment[]>([]);
  const [emailSubject, setEmailSubject] = useState("");
  const [bodyEmail, setBodyEmail] = useState("");
  const [bodyWhatsapp, setBodyWhatsapp] = useState("");
  const [channel, setChannel] = useState("both");
  const [segmentKey, setSegmentKey] = useState("followers");
  const [events, setEvents] = useState<EventItem[]>([]);
  const [contextEventId, setContextEventId] = useState("");
  const [aiNotes, setAiNotes] = useState("");
  const [personalizeWithName, setPersonalizeWithName] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitAction, setSubmitAction] = useState<"draft" | "send" | null>(null);

  const canSendEmail = channel === "email" || channel === "both";
  const subjectPreview = emailSubject.trim() || "Your subject will appear here";
  // Super-admin sessions use the Full pack (scopes include credentials, pack === "full").
  // Only treat as limited when the pack is known and is not full — never block on missing scopes.
  const unrestrictedImpersonation = hasUnrestrictedImpersonation(
    impersonation?.scopes,
    impersonation?.pack,
  );
  const packKnown = Boolean(
    impersonation?.pack || (impersonation?.scopes && impersonation.scopes.length > 0),
  );
  const canMutateCrmWhileImpersonating =
    !isImpersonating ||
    !packKnown ||
    unrestrictedImpersonation ||
    hasImpersonationScope(impersonation?.scopes, IMPERSONATION_SCOPE_HOST_EVENTS) ||
    impersonation?.pack === "host_events";
  /** Real inbox delivery while impersonating: Full pack (super admin) only. */
  const canDispatchWhileImpersonating =
    !isImpersonating || !packKnown || unrestrictedImpersonation;
  const showSendButton = canSendEmail && canDispatchWhileImpersonating;

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
    if (!emailSubject.trim()) {
      setError(
        canSendEmail
          ? "Add an email subject — recipients see this in their inbox."
          : "Add a title for this announcement.",
      );
      return;
    }
    if (bodyEmail.trim().length < 5) {
      setError("Email body must be at least 5 characters.");
      return;
    }
    if (isImpersonating && !canMutateCrmWhileImpersonating) {
      setError(
        `${IMPERSONATION_BLOCKED} Use a View + host events (or Full) impersonation pack to create drafts.`,
      );
      return;
    }
    if (sendEmail && isImpersonating && !canDispatchWhileImpersonating) {
      setError(
        `${IMPERSONATION_BLOCKED} Sending marketing email requires the Full impersonation pack. You can still create a draft.`,
      );
      return;
    }
    setSubmitting(true);
    setSubmitAction(sendEmail ? "send" : "draft");
    try {
      const created = await createAnnouncement({
        title: emailSubject.trim(),
        body_email: bodyEmail,
        body_whatsapp: bodyWhatsapp || null,
        channel,
        segment_key: segmentKey,
      });
      if (sendEmail && canSendEmail) {
        try {
          const result = await dispatchAnnouncementEmail(created.id);
          const params = new URLSearchParams({
            id: created.id,
            emailed: String(result.emailed),
            skipped: String(result.skipped),
          });
          router.push(`/host/announcements?${params.toString()}`);
          return;
        } catch (dispatchErr) {
          const reason = errorDetail(
            dispatchErr,
            "Email could not be sent. Check Admin → Email settings (SMTP, not log/dev mode).",
          );
          setError(`Draft saved, but email was not sent: ${reason}`);
          setSubmitting(false);
          setSubmitAction(null);
          return;
        }
      }
      router.push(`/host/announcements?id=${created.id}`);
    } catch (err) {
      setError(
        errorDetail(
          err,
          sendEmail
            ? "Could not create or send announcement"
            : "Could not create announcement",
        ),
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
        {isImpersonating ? (
          <Alert
            tone="warning"
            title={`Impersonation — ${packLabel(impersonation?.pack)}`}
          >
            {unrestrictedImpersonation
              ? "Full pack: draft and send are allowed and audited."
              : canMutateCrmWhileImpersonating
                ? "You can create drafts. Sending marketing email requires the Full impersonation pack (so fans are not emailed from a support session)."
                : "Creating announcements is blocked on a view-only pack. Restart impersonation with View + host events (or Full)."}
          </Alert>
        ) : null}

        {error ? (
          <Alert tone="danger" title={announcementErrorTitle(error)}>
            {error}
          </Alert>
        ) : null}

        <Card className="max-w-2xl">
          <form className="space-y-8" onSubmit={onSubmitDraft}>
            <FormSection
              title="Email subject"
              description={
                canSendEmail
                  ? "This is the subject line fans see in their inbox — not an internal label."
                  : "Used as the announcement title in your history (WhatsApp has no subject)."
              }
            >
              <Input
                label={canSendEmail ? "Email subject" : "Title"}
                value={emailSubject}
                onChange={(e) => setEmailSubject(e.target.value)}
                hint={
                  canSendEmail
                    ? "Shown as the email subject. You can include {{name}} to personalize."
                    : "For your records and WhatsApp export heading."
                }
                placeholder={
                  canSendEmail
                    ? "e.g. This Saturday — doors at 8"
                    : "e.g. Weekend reminder"
                }
                required
              />
              {canSendEmail ? (
                <div className="rounded-[var(--radius-lg)] border border-border bg-surface-muted/50 px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Inbox preview
                  </p>
                  <p className="mt-1 text-sm font-semibold text-foreground">
                    {subjectPreview}
                  </p>
                </div>
              ) : null}
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
              <label className="flex cursor-pointer items-start gap-3 rounded-[var(--radius-lg)] border border-border bg-card/50 p-3">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={personalizeWithName}
                  onChange={(e) => setPersonalizeWithName(e.target.checked)}
                />
                <span className="min-w-0 space-y-1">
                  <span className="block text-sm font-semibold text-foreground">
                    Address each fan by name
                  </span>
                  <span className="block text-xs leading-relaxed text-muted-foreground">
                    Uses the given name from their Pàdéyá profile settings. Inserts{" "}
                    <code className="rounded bg-surface-muted px-1 py-0.5 text-[11px]">
                      {NAME_TOKEN}
                    </code>{" "}
                    — replaced for each recipient when you send. Never invents names.
                  </span>
                </span>
              </label>

              <HostAnnouncementAIAssist
                title={emailSubject}
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
                personalizeWithName={personalizeWithName}
                onApply={(patch) => {
                  if (patch.title) setEmailSubject(patch.title);
                  setBodyEmail(
                    personalizeWithName
                      ? insertNameToken(patch.bodyEmail)
                      : patch.bodyEmail,
                  );
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
              <div className="space-y-2">
                <Textarea
                  label="Email body"
                  value={bodyEmail}
                  onChange={(e) => setBodyEmail(e.target.value)}
                  hint="Sent to marketing opt-in recipients when dispatched — wrapped in Pàdéyá branding with your host profile link."
                  className="min-h-[140px]"
                  required
                  minLength={5}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => setBodyEmail((prev) => insertNameToken(prev))}
                >
                  Insert {NAME_TOKEN} greeting
                </Button>
              </div>
              <Textarea
                label="WhatsApp body (optional)"
                value={bodyWhatsapp}
                onChange={(e) => setBodyWhatsapp(e.target.value)}
                hint="Short copy for manual WhatsApp broadcast. Name tokens work if you paste them here for export."
                className="min-h-[100px]"
                placeholder="Short copy for manual WhatsApp broadcast"
              />
            </FormSection>

            <div className="sticky bottom-0 -mx-5 flex flex-col gap-3 border-t border-border bg-card/95 px-5 py-4 backdrop-blur-sm sm:-mx-6 sm:flex-row sm:flex-wrap sm:items-center sm:px-6">
              {showSendButton ? (
                <Button
                  type="button"
                  disabled={submitting || !canMutateCrmWhileImpersonating}
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
                variant={showSendButton ? "secondary" : "primary"}
                disabled={submitting || !canMutateCrmWhileImpersonating}
                className="w-full sm:order-1 sm:w-auto"
              >
                {submitting && submitAction === "draft"
                  ? "Creating…"
                  : "Create draft + recipients"}
              </Button>
              {canSendEmail ? (
                <p className="text-xs text-muted-foreground sm:order-3 sm:basis-full">
                  {isImpersonating && !canDispatchWhileImpersonating
                    ? "Send is hidden during this impersonation pack. Create a draft here, or restart with Full pack to dispatch."
                    : `Send uses marketing opt-in only. Fans who opt in after this page still count when you dispatch. Subject and body are personalized per recipient when you use ${NAME_TOKEN}.`}
                </p>
              ) : null}
            </div>
          </form>
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
