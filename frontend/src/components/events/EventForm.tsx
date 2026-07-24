"use client";

/**
 * @deprecated Use Event Studio (`components/events/studio`) for host create/edit.
 * Kept only for reference; do not wire new routes to this form.
 */

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  Alert,
  Button,
  Card,
  Container,
  Input,
  Media,
  Select,
  Textarea,
} from "@/components/ui";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import { fetchCategories } from "@/lib/events-api";
import type { EventCategory, EventItem } from "@/lib/types/events";

export type EventFormValues = {
  title: string;
  description: string;
  category_id: string;
  start_datetime: string;
  end_datetime: string;
  venue_name: string;
  address: string;
  city: string;
  state: string;
  banner_url: string;
  capacity: string;
  refund_policy: string;
  age_restriction: string;
  seo_title: string;
  seo_description: string;
};

const empty: EventFormValues = {
  title: "",
  description: "",
  category_id: "",
  start_datetime: "",
  end_datetime: "",
  venue_name: "",
  address: "",
  city: "",
  state: "",
  banner_url: "",
  capacity: "",
  refund_policy: "",
  age_restriction: "",
  seo_title: "",
  seo_description: "",
};

function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function eventToFormValues(event: EventItem): EventFormValues {
  return {
    title: event.title,
    description: event.description,
    category_id: event.category_id ?? "",
    start_datetime: toLocalInput(event.start_datetime),
    end_datetime: toLocalInput(event.end_datetime),
    venue_name: event.venue_name ?? "",
    address: event.address ?? "",
    city: event.city ?? "",
    state: event.state ?? "",
    banner_url: event.banner_url ?? "",
    capacity: event.capacity?.toString() ?? "",
    refund_policy: event.refund_policy ?? "",
    age_restriction: event.age_restriction ?? "",
    seo_title: event.seo_title ?? "",
    seo_description: event.seo_description ?? "",
  };
}

export function formValuesToPayload(values: EventFormValues): Record<string, unknown> {
  return {
    title: values.title,
    description: values.description,
    category_id: values.category_id || null,
    start_datetime: new Date(values.start_datetime).toISOString(),
    end_datetime: new Date(values.end_datetime).toISOString(),
    venue_name: values.venue_name || null,
    address: values.address || null,
    city: values.city || null,
    state: values.state || null,
    banner_url: values.banner_url || null,
    capacity: values.capacity ? Number(values.capacity) : null,
    refund_policy: values.refund_policy || null,
    age_restriction: values.age_restriction || null,
    seo_title: values.seo_title || null,
    seo_description: values.seo_description || null,
    venue: values.venue_name
      ? {
          name: values.venue_name,
          address: values.address || null,
          city: values.city || null,
          state: values.state || null,
        }
      : null,
  };
}

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
    <Card className="space-y-4">
      <div>
        <h3 className="text-lg font-extrabold tracking-tight text-foreground">{title}</h3>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground sm:text-base">{description}</p>
        ) : null}
      </div>
      {children}
    </Card>
  );
}

export function EventForm({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial?: EventFormValues;
  submitLabel: string;
  onSubmit: (values: EventFormValues) => Promise<void>;
}) {
  const [values, setValues] = useState<EventFormValues>(() => initial ?? empty);
  const [categories, setCategories] = useState<EventCategory[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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

  function setField<K extends keyof EventFormValues>(key: K, value: EventFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save event");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="space-y-5 pb-24" onSubmit={handleSubmit}>
      <FormSection
        title="Basics"
        description="What fans see first on Pàdéyá — title, category, and story."
      >
        <Input
          label="Title"
          required
          value={values.title}
          onChange={(e) => setField("title", e.target.value)}
        />
        <Textarea
          label="Description"
          required
          minLength={10}
          rows={5}
          value={values.description}
          onChange={(e) => setField("description", e.target.value)}
        />
        <Select
          label="Category"
          value={values.category_id}
          onChange={(e) => setField("category_id", e.target.value)}
        >
          <option value="">Select category</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </Select>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Starts"
            type="datetime-local"
            required
            value={values.start_datetime}
            onChange={(e) => setField("start_datetime", e.target.value)}
          />
          <Input
            label="Ends"
            type="datetime-local"
            required
            value={values.end_datetime}
            onChange={(e) => setField("end_datetime", e.target.value)}
          />
        </div>
      </FormSection>

      <FormSection title="Venue" description="Where the night happens.">
        <Input
          label="Venue name"
          value={values.venue_name}
          onChange={(e) => setField("venue_name", e.target.value)}
        />
        <Input
          label="Address"
          value={values.address}
          onChange={(e) => setField("address", e.target.value)}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="City"
            value={values.city}
            onChange={(e) => setField("city", e.target.value)}
          />
          <Input
            label="State"
            value={values.state}
            onChange={(e) => setField("state", e.target.value)}
          />
        </div>
      </FormSection>

      <FormSection
        title="Media & capacity"
        description="Upload a banner or paste a URL — preview updates instantly."
      >
        <ImageUrlOrUploadField
          label="Banner image"
          hint="Use a wide image (roughly 21:9) for best results."
          value={values.banner_url}
          onChange={(url) => setField("banner_url", url)}
          mediaType="banner"
          setAsBanner
          showPreview={false}
        />
        <div className="overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface-dark">
          <div className="relative aspect-[21/9] min-h-[120px]">
            {values.banner_url ? (
              <Media src={values.banner_url} alt="" className="opacity-90" />
            ) : (
              <div className="padeya-hero-glow absolute inset-0" />
            )}
          </div>
          {!values.banner_url ? (
            <p className="px-4 py-3 text-sm text-subtle-foreground">
              Banner preview appears here once you upload or paste an image.
            </p>
          ) : null}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Capacity"
            type="number"
            min={1}
            hint="Optional hard cap for the night"
            value={values.capacity}
            onChange={(e) => setField("capacity", e.target.value)}
          />
          <Input
            label="Age restriction"
            hint="e.g. 18+, 21+"
            value={values.age_restriction}
            onChange={(e) => setField("age_restriction", e.target.value)}
          />
        </div>
      </FormSection>

      <FormSection title="Policies & SEO" description="Refunds and discovery copy shown on the public page.">
        <Input
          label="Refund policy"
          hint="Be clear — buyers see this before checkout"
          value={values.refund_policy}
          onChange={(e) => setField("refund_policy", e.target.value)}
        />
        <Input
          label="SEO title"
          hint="Optional — defaults to the event title"
          value={values.seo_title}
          onChange={(e) => setField("seo_title", e.target.value)}
        />
        <Textarea
          label="SEO description"
          hint="Optional short blurb for search snippets"
          rows={3}
          value={values.seo_description}
          onChange={(e) => setField("seo_description", e.target.value)}
        />
      </FormSection>

      {error ? (
        <Alert tone="danger" title="Could not save event">
          {error}
        </Alert>
      ) : null}

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card/95 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur md:static md:border-0 md:bg-transparent md:p-0 md:backdrop-blur-none">
        <Container className="flex items-center justify-between gap-3 !px-0 md:justify-start">
          <p className="hidden text-sm text-muted-foreground sm:block md:hidden">
            Review sections above, then save.
          </p>
          <Button type="submit" size="lg" disabled={submitting} className="w-full sm:w-auto">
            {submitting ? "Saving…" : submitLabel}
          </Button>
        </Container>
      </div>
    </form>
  );
}
