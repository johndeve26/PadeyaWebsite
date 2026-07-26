"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Button,
  Container,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import {
  createTicketType,
  fetchCategories,
  fetchTicketTypes,
  updateTicketType,
} from "@/lib/events-api";
import { fetchMyHost } from "@/lib/hosts-api";
import type {
  EventCategory,
  EventItem,
  EventPublishChecklist,
} from "@/lib/types/events";

import {
  buildLocalPublishChecklist,
  missingChecklistLabels,
  previewCheckedStorageKey,
} from "./checklist-utils";
import { EventStudioShell } from "./EventStudioShell";
import { BasicsStep } from "./steps/BasicsStep";
import { LineupStep } from "./steps/LineupStep";
import { LocationStep } from "./steps/LocationStep";
import { MediaStep } from "./steps/MediaStep";
import { MerchandiseStep } from "./steps/MerchandiseStep";
import { PoliciesStep } from "./steps/PoliciesStep";
import { PublishStep } from "./steps/PublishStep";
import { QuestionsStep } from "./steps/QuestionsStep";
import { ScheduleStep } from "./steps/ScheduleStep";
import { SeoStep } from "./steps/SeoStep";
import { TicketsStep } from "./steps/TicketsStep";
import {
  agendaEndAfterStartError,
  emptyStudioValues,
  parseStudioStep,
  policyFieldsError,
  studioStepCompletion,
  studioValuesToPayload,
  ticketDraftToPayload,
  ticketHasSales,
  ticketSaleWindowError,
  ticketsToStudioDrafts,
  type EventStudioValues,
  type StudioStepId,
  STUDIO_STEPS,
} from "./types";

function softStepWarning(
  step: StudioStepId,
  values: EventStudioValues,
): string | null {
  if (step === "schedule") {
    if (!values.start_datetime || !values.end_datetime) {
      return "Set start and end times before continuing.";
    }
    if (agendaEndAfterStartError(values.start_datetime, values.end_datetime)) {
      return "End time must be after start time.";
    }
    const badAgenda = values.agenda_items.find((item) =>
      agendaEndAfterStartError(item.start_time, item.end_time),
    );
    if (badAgenda) {
      return `Agenda item “${badAgenda.title || "Untitled"}” must end after it starts.`;
    }
  }
  if (step === "policies") {
    return policyFieldsError(values);
  }
  const done = studioStepCompletion(values);
  if (done[step]) return null;
  switch (step) {
    case "basics":
      return "Add a title and a richer description before continuing.";
    case "location":
      return "Add a venue, public location label, or taxonomy place — or set online-only privacy.";
    case "tickets":
      return "Add at least one ticket tier when you can — you can still continue.";
    default:
      return null;
  }
}

type EventStudioProps = {
  initial?: EventStudioValues;
  eventId?: string;
  eventStatus?: string | null;
  checklist?: EventPublishChecklist | null;
  mode: "create" | "edit";
  onSave: (
    values: EventStudioValues,
    payload: Record<string, unknown>,
  ) => Promise<EventItem>;
  onSubmitReview?: (eventId: string) => Promise<void>;
  onPublish?: (eventId: string) => Promise<void>;
  onArchiveDraft?: (eventId: string) => Promise<void>;
  onDeleteDraft?: (eventId: string) => Promise<void>;
};

function EventStudioInner({
  initial,
  eventId,
  eventStatus,
  checklist,
  mode,
  onSave,
  onSubmitReview,
  onPublish,
  onArchiveDraft,
  onDeleteDraft,
}: EventStudioProps) {
  const { user, isImpersonating } = useAuth();
  const hostEventsAllowed =
    !isImpersonating ||
    Boolean(user?.impersonation?.scopes?.includes("host_events"));
  const toast = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const errorBannerRef = useRef<HTMLDivElement | null>(null);

  const step = parseStudioStep(searchParams.get("step"));
  const [values, setValues] = useState<EventStudioValues>(() => {
    const base = initial ?? emptyStudioValues();
    if (base.preview_checked || typeof window === "undefined") return base;
    const key = previewCheckedStorageKey(eventId);
    if (key && window.sessionStorage.getItem(key) === "1") {
      return { ...base, preview_checked: true };
    }
    return base;
  });
  const [categories, setCategories] = useState<EventCategory[]>([]);
  const [error, setError] = useState<string | null>(null);

  function surfaceStudioError(err: unknown, fallback = "Unable to save event") {
    const message =
      err instanceof ApiError
        ? err.detail
        : err instanceof Error
          ? err.message
          : fallback;
    setError(message);
    toast.push({
      tone: "danger",
      title: "Could not save event",
      description: message,
      durationMs: 8000,
    });
    // Banner is below the form — bring it into view after layout paints.
    window.setTimeout(() => {
      errorBannerRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }, 50);
  }
  const [stepHint, setStepHint] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [savedChecklist, setSavedChecklist] = useState(checklist ?? null);
  const [previewing, setPreviewing] = useState(false);
  const [savedEventId, setSavedEventId] = useState<string | undefined>(eventId);
  const ticketsHydrated = useRef(
    Boolean(initial?.ticket_drafts?.some((d) => d.id)),
  );
  const canPublish = Boolean(
    onPublish &&
      userHasPermission(user, "events.approve", "admin.full_access"),
  );
  const draftLike =
    !eventStatus || eventStatus === "draft" || eventStatus === "rejected";

  useEffect(() => {
    const key = previewCheckedStorageKey(savedEventId || eventId);
    if (!key || typeof window === "undefined") return;
    window.sessionStorage.setItem(key, values.preview_checked ? "1" : "0");
  }, [values.preview_checked, savedEventId, eventId]);

  useEffect(() => {
    let active = true;
    void fetchCategories()
      .then((items) => {
        if (active) setCategories(items);
      })
      .catch(() => {
        if (active) setCategories([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!savedEventId || ticketsHydrated.current) return;
    let active = true;
    void fetchTicketTypes(savedEventId)
      .then((items) => {
        if (!active) return;
        ticketsHydrated.current = true;
        if (items.length === 0) return;
        setValues((prev) => {
          if (prev.ticket_drafts.some((d) => d.id)) return prev;
          return { ...prev, ticket_drafts: ticketsToStudioDrafts(items) };
        });
      })
      .catch(() => {
        ticketsHydrated.current = true;
      });
    return () => {
      active = false;
    };
  }, [savedEventId]);

  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  function setField<K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) {
    setDirty(true);
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function goToStep(next: StudioStepId) {
    setStepHint(null);
    const params = new URLSearchParams(searchParams.toString());
    if (next === "basics") params.delete("step");
    else params.set("step", next);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function handleContinue() {
    const warning = softStepWarning(step, values);
    if (warning && (step === "basics" || step === "schedule")) {
      setStepHint(warning);
      setError(null);
      return;
    }
    if (warning) setStepHint(warning);
    else setStepHint(null);
    const idx = STUDIO_STEPS.findIndex((s) => s.id === step);
    if (idx < STUDIO_STEPS.length - 1) {
      goToStep(STUDIO_STEPS[idx + 1].id);
    }
  }

  const applyHostDefaults = useCallback(() => {
    void fetchMyHost()
      .then((host) => {
        if (!host) return;
        setDirty(true);
        setValues((prev) => {
          const next = { ...prev };
          if (!next.city && host.profile?.city) next.city = host.profile.city;
          if (!next.state && host.profile?.state) next.state = host.profile.state;
          const niche = host.taxonomy?.niche_positioning;
          if (!next.vibe && niche) next.vibe = niche;
          const catSlug = host.taxonomy?.category_slugs?.[0];
          if (!next.category_id && catSlug) {
            const match = categories.find((c) => c.slug === catSlug);
            if (match) next.category_id = match.id;
          }
          return next;
        });
      })
      .catch(() => undefined);
  }, [categories]);

  const stepIndex = STUDIO_STEPS.findIndex((s) => s.id === step);

  async function syncTickets(
    targetEventId: string,
    drafts: EventStudioValues["ticket_drafts"],
  ) {
    const next = [...drafts];
    for (let index = 0; index < next.length; index += 1) {
      const draft = next[index];
      if (!draft.name.trim()) continue;
      if (!draft.type.trim()) {
        throw new Error(
          `Ticket tier "${draft.name}" needs a type (preset or custom).`,
        );
      }
      if (ticketSaleWindowError(draft.sale_start, draft.sale_end)) {
        throw new Error(
          `Ticket tier "${draft.name}" sale end must be after sale start.`,
        );
      }
      const sold = ticketHasSales(draft);
      // host_events pack may patch price/qty after sales for support.
      const canStructural = isImpersonating && hostEventsAllowed;
      const body = ticketDraftToPayload(draft, {
        forSoldTier: sold && !canStructural,
      });
      if (draft.id) {
        const updated = await updateTicketType(targetEventId, draft.id, body);
        next[index] = {
          ...draft,
          id: updated.id,
          quantity_sold: updated.quantity_sold ?? draft.quantity_sold,
          quantity_reserved:
            updated.quantity_reserved ?? draft.quantity_reserved,
          status: updated.status ?? draft.status,
        };
      } else {
        const created = await createTicketType(targetEventId, body);
        next[index] = {
          ...draft,
          id: created.id,
          quantity_sold: created.quantity_sold ?? 0,
          quantity_reserved: created.quantity_reserved ?? 0,
          status: created.status ?? "active",
        };
      }
    }
    setValues((prev) => ({ ...prev, ticket_drafts: next }));
  }

  async function handleSave(options?: {
    submit?: boolean;
    publish?: boolean;
    silent?: boolean;
  }) {
    setSaving(true);
    setError(null);
    try {
      if (!values.title || values.description.length < 10) {
        throw new Error(
          "Title and a richer description are required before saving.",
        );
      }
      if (!values.start_datetime || !values.end_datetime) {
        throw new Error("Start and end times are required.");
      }
      if (
        agendaEndAfterStartError(values.start_datetime, values.end_datetime)
      ) {
        throw new Error("Event end time must be after start time.");
      }
      const badAgenda = values.agenda_items.find((item) =>
        agendaEndAfterStartError(item.start_time, item.end_time),
      );
      if (badAgenda) {
        throw new Error(
          `Agenda item “${badAgenda.title || "Untitled"}” must end after it starts.`,
        );
      }
      const policyError = policyFieldsError(values);
      if (policyError) {
        throw new Error(policyError);
      }
      if (options?.submit || options?.publish) {
        const checklistNow = buildLocalPublishChecklist(values, savedChecklist);
        if (options.publish) {
          checklistNow.preview_checked = values.preview_checked;
        }
        const missing = missingChecklistLabels({
          ...checklistNow,
          preview_checked: values.preview_checked,
          ready_to_submit: false,
        });
        // Recompute ready with current preview flag
        if (missing.length > 0) {
          throw new Error(
            `Finish the publishing checklist first: ${missing.join(" · ")}`,
          );
        }
      }
      if (
        options?.submit &&
        values.visibility === "listed" &&
        !values.category_id
      ) {
        throw new Error(
          "Primary category is required before submitting a listed event.",
        );
      }
      const onlineOrHybrid =
        values.event_type === "online" || values.event_type === "hybrid";
      if (
        (options?.submit || options?.publish) &&
        !onlineOrHybrid &&
        !values.city.trim()
      ) {
        throw new Error("City is required for in-person events before submit.");
      }
      const payload = studioValuesToPayload(values, {
        includeSlug: mode === "edit" && Boolean(values.slug.trim()),
        categoryName:
          categories.find((c) => c.id === values.category_id)?.name ?? null,
      });
      const saved = await onSave(values, payload);
      await syncTickets(saved.id, values.ticket_drafts);
      setSavedEventId(saved.id);
      setSavedChecklist(saved.publish_checklist ?? null);
      setDirty(false);
      setLastSavedAt(
        new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      );
      if (mode === "create" && pathname.includes("/new") && !options?.submit && !options?.publish) {
        const params = new URLSearchParams();
        if (step !== "basics") params.set("step", step);
        const qs = params.toString();
        router.replace(
          `/host/events/${saved.id}/edit${qs ? `?${qs}` : ""}`,
        );
      }
      if (options?.publish && onPublish) {
        await onPublish(saved.id);
      } else if (options?.submit && onSubmitReview) {
        await onSubmitReview(saved.id);
      }
      if (!options?.silent) {
        toast.push({
          tone: "success",
          title: options?.publish
            ? "Event published"
            : options?.submit
              ? "Event published"
              : "Draft saved",
          durationMs: 3500,
        });
      }
      return saved;
    } catch (err) {
      surfaceStudioError(err);
      throw err;
    } finally {
      setSaving(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await handleSave();
    } catch {
      /* surfaced */
    }
  }

  async function handleOpenPreview() {
    setPreviewing(true);
    setError(null);
    try {
      // Already saved & clean: open the real preview URL in one shot (no about:blank).
      if (savedEventId && !dirty) {
        window.open(
          `/host/events/${savedEventId}/preview`,
          "_blank",
          "noopener,noreferrer",
        );
        return;
      }

      // Need a save first. Open a same-origin tab during the click gesture when
      // we already have an id, then navigate after save — avoids about:blank and
      // keeps the popup tied to the user gesture. (`noopener` would return null
      // and block later navigation, so we clear opener manually.)
      let tab: Window | null = null;
      if (savedEventId) {
        tab = window.open(`/host/events/${savedEventId}/preview`, "_blank");
        if (tab) tab.opener = null;
      }

      toast.push({
        tone: "info",
        title: "Saving…",
        description: "Opening preview after your draft is saved.",
        durationMs: 4000,
      });
      const saved = await handleSave({ silent: true });
      const url = `/host/events/${saved.id}/preview`;

      if (tab && !tab.closed) {
        tab.location.assign(url);
        return;
      }

      tab = window.open(url, "_blank");
      if (tab) {
        tab.opener = null;
      } else {
        toast.push({
          tone: "warning",
          title: "Preview blocked",
          description: "Allow pop-ups for this site, then try Preview again.",
          durationMs: 6000,
        });
      }
    } catch {
      /* surfaced by handleSave */
    } finally {
      setPreviewing(false);
    }
  }

  const localChecklist = useMemo(
    () => buildLocalPublishChecklist(values, savedChecklist),
    [values, savedChecklist],
  );

  const missingPublish = useMemo(
    () => missingChecklistLabels(localChecklist),
    [localChecklist],
  );

  const navFooter = (
    <div className="hidden flex-wrap items-center justify-between gap-3 border-t border-border pt-4 lg:flex">
      <Button
        type="button"
        variant="ghost"
        disabled={stepIndex <= 0}
        onClick={() => goToStep(STUDIO_STEPS[stepIndex - 1].id)}
      >
        Back
      </Button>
      <div className="flex flex-wrap gap-2">
        <Button
          type="submit"
          variant="secondary"
          disabled={saving || !hostEventsAllowed}
        >
          {saving ? "Saving…" : "Save draft"}
        </Button>
        {stepIndex < STUDIO_STEPS.length - 1 ? (
          <Button type="button" onClick={handleContinue}>
            Continue
          </Button>
        ) : (
          <Button
            type="button"
            disabled={
              saving || !hostEventsAllowed || !localChecklist.ready_to_submit
            }
            onClick={() =>
              void handleSave({ submit: Boolean(onSubmitReview) }).catch(
                () => undefined,
              )
            }
          >
            {onSubmitReview ? "Save & submit" : "Save"}
          </Button>
        )}
      </div>
    </div>
  );

  const mobileBar = (
    <Container className="flex items-center justify-between gap-2 !px-0">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled={stepIndex <= 0}
        onClick={() => goToStep(STUDIO_STEPS[stepIndex - 1].id)}
      >
        Back
      </Button>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={saving || !hostEventsAllowed}
          onClick={() => void handleSave().catch(() => undefined)}
        >
          {saving ? "Saving…" : "Save"}
        </Button>
        {stepIndex < STUDIO_STEPS.length - 1 ? (
          <Button type="button" size="sm" onClick={handleContinue}>
            Continue
          </Button>
        ) : (
          <Button
            type="button"
            size="sm"
            disabled={
              saving || !hostEventsAllowed || !localChecklist.ready_to_submit
            }
            onClick={() =>
              void handleSave({ submit: Boolean(onSubmitReview) }).catch(
                () => undefined,
              )
            }
          >
            Submit
          </Button>
        )}
      </div>
    </Container>
  );

  return (
    <form onSubmit={onSubmit}>
      <EventStudioShell
        title={
          mode === "create"
            ? "Create with Event Studio"
            : values.title || "Edit event"
        }
        description="Fill in each step, then use Preview to open the full guest listing in a new tab. Publish goes live immediately — Pàdéyá may review listings after they are public."
        currentStep={step}
        onStepChange={goToStep}
        values={values}
        lastSavedAt={lastSavedAt}
        dirty={dirty}
        saving={saving}
        onSaveDraft={() => void handleSave().catch(() => undefined)}
        footer={navFooter}
        mobileBar={mobileBar}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={previewing || saving}
              onClick={() => void handleOpenPreview()}
            >
              {previewing ? "Opening…" : "Preview"}
            </Button>
            <Button
              type="submit"
              variant="secondary"
              disabled={saving || !hostEventsAllowed}
            >
              {saving ? "Saving…" : "Save draft"}
            </Button>
            {savedEventId || mode === "edit" ? (
              <Button
                type="button"
                disabled={
                  saving || !hostEventsAllowed || !localChecklist.ready_to_submit
                }
                onClick={() =>
                  void handleSave({ submit: true }).catch(() => undefined)
                }
              >
                Publish event
              </Button>
            ) : null}
            {canPublish ? (
              <Button
                type="button"
                disabled={
                  saving || !hostEventsAllowed || !localChecklist.ready_to_submit
                }
                onClick={() =>
                  void handleSave({ publish: true }).catch(() => undefined)
                }
              >
                Publish
              </Button>
            ) : null}
          </div>
        }
      >
        {isImpersonating && !hostEventsAllowed ? (
          <Alert tone="warning" title="View-only impersonation pack">
            Your session can browse host tools but cannot save or publish events.
            Ask for the host_events pack (operations / admin) if you need to edit.
          </Alert>
        ) : null}
        {step === "publish" && missingPublish.length > 0 ? (
          <Alert tone="info" title="Validation summary">
            Still needed: {missingPublish.join(" · ")}
          </Alert>
        ) : null}
        {step === "basics" ? (
          <BasicsStep
            values={values}
            categories={categories}
            mode={mode}
            eventId={savedEventId}
            onChange={setField}
            onApplyHostDefaults={applyHostDefaults}
          />
        ) : null}
        {step === "location" ? (
          <LocationStep values={values} onChange={setField} />
        ) : null}
        {step === "schedule" ? (
          <ScheduleStep values={values} onChange={setField} />
        ) : null}
        {step === "tickets" ? (
          <TicketsStep
            values={values}
            eventId={savedEventId}
            onChange={setField}
            allowStructuralEdits={Boolean(
              isImpersonating && hostEventsAllowed,
            )}
          />
        ) : null}
        {step === "media" ? (
          <MediaStep
            values={values}
            eventId={savedEventId}
            onChange={setField}
          />
        ) : null}
        {step === "lineup" ? (
          <LineupStep
            values={values}
            eventId={savedEventId}
            onChange={setField}
          />
        ) : null}
        {step === "questions" ? (
          <QuestionsStep values={values} onChange={setField} />
        ) : null}
        {step === "policies" ? (
          <PoliciesStep values={values} onChange={setField} />
        ) : null}
        {step === "seo" ? (
          <SeoStep
            values={values}
            categories={categories}
            onChange={setField}
          />
        ) : null}
        {step === "merchandise" ? (
          <MerchandiseStep eventId={savedEventId} />
        ) : null}
        {step === "publish" ? (
          <PublishStep
            values={values}
            checklist={localChecklist}
            eventId={savedEventId}
            eventStatus={eventStatus}
            previewing={previewing}
            saving={saving}
            canPublish={canPublish}
            canArchiveDraft={Boolean(onArchiveDraft && draftLike && savedEventId)}
            canDeleteDraft={Boolean(onDeleteDraft && draftLike && savedEventId)}
            onPreviewChecked={(value) => setField("preview_checked", value)}
            onOpenPreview={() => void handleOpenPreview()}
            onSaveDraft={() => void handleSave().catch(() => undefined)}
            onSubmitReview={() =>
              void handleSave({ submit: true }).catch(() => undefined)
            }
            onPublish={
              canPublish
                ? () => void handleSave({ publish: true }).catch(() => undefined)
                : undefined
            }
            onArchiveDraft={
              onArchiveDraft && savedEventId
                ? () => onArchiveDraft(savedEventId)
                : undefined
            }
            onDeleteDraft={
              onDeleteDraft && savedEventId
                ? () => onDeleteDraft(savedEventId)
                : undefined
            }
          />
        ) : null}

        {stepHint ? (
          <Alert tone="warning" title="Almost there">
            {stepHint}
          </Alert>
        ) : null}
        {error ? (
          <div ref={errorBannerRef}>
            <Alert tone="danger" title="Could not save event">
              {error}
            </Alert>
          </div>
        ) : null}
      </EventStudioShell>
    </form>
  );
}

export function EventStudio(props: EventStudioProps) {
  return (
    <Suspense
      fallback={
        <div className="max-w-3xl">
          <SkeletonLoader lines={10} />
        </div>
      }
    >
      <EventStudioInner {...props} />
    </Suspense>
  );
}
