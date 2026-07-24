"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  emptyVaultValues,
  toVaultPayload,
  type VaultItemEditorValues,
} from "@/components/vault/studio/VaultItemEditor";
import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyEvents } from "@/lib/events-api";
import { upsertLegacyFeaturedItem } from "@/lib/legacy-api";
import { fetchHostMemory } from "@/lib/memories-api";
import type { EventItem } from "@/lib/types/events";
import { VAULT_HOST_STUDIO_DESCRIPTION } from "@/lib/vault-copy";
import {
  archiveHostVaultItem,
  createHostVaultItem,
  publishHostVaultItem,
  scheduleHostVaultItem,
  updateHostVaultItem,
} from "@/lib/vault-api";

import { VaultCreatorStepper } from "./VaultCreatorStepper";
import { AccessStep } from "./steps/AccessStep";
import { ContentStep } from "./steps/ContentStep";
import { MediaStep } from "./steps/MediaStep";
import { PreviewPublishStep } from "./steps/PreviewPublishStep";
import { RelatedEventStep } from "./steps/RelatedEventStep";
import {
  buildVaultPublishChecklist,
  parseVaultCreatorStep,
  VAULT_CREATOR_STEPS,
  vaultCreatorStepCompletion,
  type VaultCreatorStepId,
} from "./types";

type MemoryOption = { id: string; label: string };

export function VaultCreator() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const step = parseVaultCreatorStep(searchParams.get("step"));
  const [values, setValues] = useState<VaultItemEditorValues>(emptyVaultValues);
  const [itemId, setItemId] = useState<string | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [memories, setMemories] = useState<MemoryOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewChecked, setPreviewChecked] = useState(false);
  const [scheduleAt, setScheduleAt] = useState("");

  const completed = useMemo(() => vaultCreatorStepCompletion(values), [values]);
  const stepIndex = VAULT_CREATOR_STEPS.findIndex((s) => s.id === step);
  const stepMeta = VAULT_CREATOR_STEPS[stepIndex];
  const checklist = useMemo(
    () => buildVaultPublishChecklist(values, { previewChecked }),
    [values, previewChecked],
  );
  const canPublish = checklist.every((item) => !item.required || item.done);

  const memoryEventIds = useMemo(
    () =>
      values.related_event_id
        ? [values.related_event_id]
        : events.slice(0, 12).map((event) => event.id),
    [events, values.related_event_id],
  );

  const memoriesForSelect = useMemo(
    () => (memoryEventIds.length === 0 ? [] : memories),
    [memoryEventIds, memories],
  );

  useEffect(() => {
    let active = true;
    void fetchMyEvents()
      .then((rows) => {
        if (active) setEvents(rows);
      })
      .catch(() => {
        if (active) setEvents([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (memoryEventIds.length === 0) return;
    let active = true;

    void (async () => {
      const options: MemoryOption[] = [];
      await Promise.all(
        memoryEventIds.map(async (eventId) => {
          try {
            const memory = await fetchHostMemory(eventId);
            const event = events.find((e) => e.id === eventId);
            options.push({
              id: memory.id,
              label: event?.title || memory.event_title || "Event memory",
            });
          } catch {
            // Event has no memory yet
          }
        }),
      );
      if (active) setMemories(options);
    })();

    return () => {
      active = false;
    };
  }, [events, memoryEventIds]);

  function goTo(next: VaultCreatorStepId) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "content") params.delete("step");
    else params.set("step", next);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  async function persist(
    nextValues: VaultItemEditorValues,
    successNote: string,
    options?: { redirectToDetail?: boolean },
  ) {
    const redirectToDetail = Boolean(options?.redirectToDetail);
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const payload = toVaultPayload(nextValues);
      const item = itemId
        ? await updateHostVaultItem(itemId, payload)
        : await createHostVaultItem(payload);
      setItemId(item.id);
      setValues({
        ...nextValues,
        slug: item.slug || nextValues.slug,
        status: item.status || nextValues.status,
      });

      if (nextValues.feature_on_legacy) {
        await upsertLegacyFeaturedItem({
          item_type: "vault_item",
          item_id: item.id,
          placement: "featured_vault_item",
        });
      }

      setNote(successNote);
      if (redirectToDetail) {
        router.push(`/host/vault/${item.id}`);
      }
      return item;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft() {
    const next = { ...values, status: "draft" };
    setValues(next);
    await persist(next, itemId ? "Draft updated" : "Draft saved");
  }

  async function publishNow() {
    if (!canPublish) {
      setError("Finish the publish checklist before going live.");
      goTo("publish");
      return;
    }
    const next = { ...values, status: "draft" };
    setValues(next);
    const saved = await persist(next, "Preparing publish…");
    if (!saved) return;
    setBusy(true);
    setError(null);
    try {
      const item = await publishHostVaultItem(saved.id);
      setItemId(item.id);
      setValues({ ...next, status: item.status, slug: item.slug });
      setNote("Drop published");
      router.push(`/host/vault/${item.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Publish failed");
    } finally {
      setBusy(false);
    }
  }

  async function schedulePublish() {
    if (!canPublish) {
      setError("Finish the publish checklist before scheduling.");
      goTo("publish");
      return;
    }
    const start = scheduleAt || values.access.starts_at;
    if (!start) {
      setError("Set a go-live / access start time to schedule.");
      goTo("publish");
      return;
    }
    const next: VaultItemEditorValues = {
      ...values,
      status: "draft",
      access: { ...values.access, starts_at: start },
    };
    setValues(next);
    setScheduleAt(start);
    const saved = await persist(next, "Preparing schedule…");
    if (!saved) return;
    setBusy(true);
    setError(null);
    try {
      const iso = new Date(start).toISOString();
      const item = await scheduleHostVaultItem(saved.id, iso);
      setItemId(item.id);
      setValues({ ...next, status: item.status, slug: item.slug });
      setNote("Drop scheduled");
      router.push(`/host/vault/${item.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Schedule failed");
    } finally {
      setBusy(false);
    }
  }

  async function archiveDrop() {
    if (!itemId) {
      setError("Save a draft before archiving.");
      return;
    }
    if (!confirm("Archive this drop? It leaves the public Vault.")) return;
    setBusy(true);
    setError(null);
    try {
      await archiveHostVaultItem(itemId);
      router.push("/host/vault");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Archive failed");
      setBusy(false);
    }
  }

  function softStepWarning(): string | null {
    if (step === "content" && !completed.content) {
      return "Add a title and teaser, description, or body before continuing.";
    }
    if (step === "access" && !completed.access) {
      return "Fix access rules — invite codes and paid prices are required when selected.";
    }
    if (step === "media") {
      if (
        values.content_type === "file_download" &&
        !values.file_url.trim()
      ) {
        return "File download drops need a file URL.";
      }
      if (
        values.content_type === "external_link" &&
        !values.external_url.trim()
      ) {
        return "External link drops need an external URL.";
      }
    }
    return null;
  }

  function continueNext() {
    const warning = softStepWarning();
    if (warning) {
      setError(warning);
      return;
    }
    setError(null);
    const next = VAULT_CREATOR_STEPS[stepIndex + 1];
    if (next) goTo(next.id);
  }

  function backPrev() {
    setError(null);
    const prev = VAULT_CREATOR_STEPS[stepIndex - 1];
    if (prev) goTo(prev.id);
  }

  return (
    <VaultStudioShell
      title="Create Vault drop"
      description={VAULT_HOST_STUDIO_DESCRIPTION}
      actions={
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => void saveDraft()}
          >
            Save draft
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={busy}
            onClick={() => goTo("publish")}
          >
            Preview
          </Button>
          <Link href="/host/vault">
            <Button size="sm" variant="ghost">
              Studio
            </Button>
          </Link>
        </div>
      }
    >
      <div className="relative mb-6 overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-6 text-paper sm:px-7">
        <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-70" />
        <div className="relative space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
            Vault Creator
          </p>
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
            Step {stepIndex + 1} of {VAULT_CREATOR_STEPS.length}
            <span className="text-subtle-foreground"> · {stepMeta?.label}</span>
          </h2>
          <p className="max-w-xl text-sm text-subtle-foreground">
            {stepMeta?.description}
            {itemId ? " · Draft linked to this session" : ""}
          </p>
        </div>
      </div>

      {error ? (
        <Alert tone="danger" title="Creator needs attention" className="mb-6">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Saved" className="mb-6">
          {note}
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-4 lg:self-start">
          <VaultCreatorStepper
            current={step}
            completed={completed}
            onSelect={goTo}
          />
        </aside>

        <Card className="space-y-8">
          {step === "content" ? (
            <ContentStep values={values} onChange={setValues} />
          ) : null}
          {step === "media" ? (
            <MediaStep values={values} onChange={setValues} />
          ) : null}
          {step === "access" ? (
            <AccessStep values={values} onChange={setValues} events={events} />
          ) : null}
          {step === "related" ? (
            <RelatedEventStep
              values={values}
              onChange={setValues}
              events={events}
              memories={memoriesForSelect}
            />
          ) : null}
          {step === "publish" ? (
            <PreviewPublishStep
              values={values}
              onChange={setValues}
              previewChecked={previewChecked}
              onPreviewChecked={setPreviewChecked}
              scheduleAt={scheduleAt || values.access.starts_at}
              onScheduleAtChange={setScheduleAt}
            />
          ) : null}

          <div className="flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="ghost"
                disabled={busy || stepIndex === 0}
                onClick={backPrev}
              >
                Back
              </Button>
              {stepIndex < VAULT_CREATOR_STEPS.length - 1 ? (
                <Button type="button" disabled={busy} onClick={continueNext}>
                  Continue
                </Button>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() => void saveDraft()}
              >
                {busy ? "Saving…" : "Save draft"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() => {
                  goTo("publish");
                  setNote("Review the three previews before publishing.");
                }}
              >
                Preview
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={busy || !canPublish}
                onClick={() => void schedulePublish()}
              >
                Schedule
              </Button>
              <Button
                type="button"
                disabled={busy || !canPublish}
                onClick={() => void publishNow()}
              >
                Publish
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="text-danger"
                disabled={busy || !itemId}
                onClick={() => void archiveDrop()}
              >
                Archive
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </VaultStudioShell>
  );
}
