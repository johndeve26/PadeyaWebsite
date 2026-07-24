"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { HostMerchProductPreview } from "@/components/merch/host/HostMerchProductPreview";
import {
  ImageUrlListUploadField,
  ImageUrlOrUploadField,
} from "@/components/media/ImageUrlOrUploadField";
import { MerchFormStepper } from "@/components/merch/host/form/MerchFormStepper";
import {
  buildPublishChecklist,
  MerchPublishChecklist,
} from "@/components/merch/host/form/MerchPublishChecklist";
import { MerchStickyActions } from "@/components/merch/host/form/MerchStickyActions";
import { MerchVariantsEditor } from "@/components/merch/host/form/MerchVariantsEditor";
import {
  MerchCategoryTagAI,
  MerchDescriptionAI,
  MerchTitleAI,
} from "@/components/merch/host/MerchAIAssist";
import {
  ACCESS_TYPE_OPTIONS,
  createDefaultVariant,
  DEFAULT_MERCH_FORM_VALUES,
  fromLocalInput,
  MERCH_FORM_SECTIONS,
  parseGallery,
  STOREFRONT_VISIBILITY_OPTIONS,
  toLocalInput,
  type MerchFormSectionId,
  type MerchProductFormValues,
  type MerchSectionStatus,
  type MerchVariantFormRow,
} from "@/components/merch/host/form/types";
import { Badge, Button, Input, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createMerchProduct,
  createMerchVariant,
  createStandaloneMerchProduct,
  fetchHostSizeCharts,
  updateMerchProduct,
  updateMerchVariant,
  type MerchProductWriteBody,
  type MerchVariantWriteBody,
} from "@/lib/merch-api";
import { MERCH_CATEGORIES, MERCH_PRODUCT_TYPES } from "@/lib/merch-product-types";
import type { MerchSizeChart } from "@/lib/merch-size-chart";
import type { MerchProduct } from "@/lib/types/merch";
import type { VaultItem } from "@/lib/types/vault";
import { fetchHostVaultItems } from "@/lib/vault-api";

export type { MerchProductFormValues } from "@/components/merch/host/form/types";

function FieldHint({ children }: { children: ReactNode }) {
  return <p className="text-xs leading-relaxed text-muted-foreground">{children}</p>;
}

function SectionShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-5 rounded-[var(--radius-lg)] border border-border bg-card p-4 sm:p-6">
      <div>
        <h3 className="text-lg font-extrabold tracking-tight text-foreground">
          {title}
        </h3>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function Expandable({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <div className="rounded-[var(--radius-md)] border border-border">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="text-sm font-extrabold text-foreground">{title}</span>
        <span className="text-xs font-bold text-muted-foreground">
          {open ? "Hide" : "Show"}
        </span>
      </button>
      {open ? (
        <div className="space-y-3 border-t border-border px-4 py-4">
          {children}
        </div>
      ) : null}
    </div>
  );
}

export function productToFormValues(product: MerchProduct): MerchProductFormValues {
  const variants: MerchVariantFormRow[] =
    product.variants.length > 0
      ? product.variants.map((v) => ({
          key: v.id,
          id: v.id,
          label: v.label ?? "One size",
          size: v.size ?? "",
          color: v.color ?? "",
          option_1_name: v.option_1_name ?? "",
          option_1_value: v.option_1_value ?? "",
          option_2_name: v.option_2_name ?? "",
          option_2_value: v.option_2_value ?? "",
          sku: v.sku ?? "",
          price_override:
            v.price_override != null || v.price != null
              ? String(v.price_override ?? v.price)
              : "",
          inventory: String(v.stock_quantity ?? v.inventory_count ?? 0),
          status: v.status || "active",
          print_on_demand_variant_ref: v.print_on_demand_variant_ref ?? "",
        }))
      : [createDefaultVariant()];

  const cover = product.cover_image_url ?? product.image_url ?? "";

  return {
    ...DEFAULT_MERCH_FORM_VALUES,
    name: product.name,
    description: product.description ?? "",
    short_description: product.short_description ?? "",
    product_type: product.product_type ?? "other",
    category: product.category ?? "",
    tags: Array.isArray(product.tags) ? product.tags : [],
    cover_image_url: cover,
    gallery_urls: (product.gallery_urls ?? []).join("\n"),
    use_fallback_visual: !cover,
    base_price: String(product.base_price),
    currency: product.currency || "NGN",
    status: product.status,
    sales_start_at: toLocalInput(product.sales_start_at),
    sales_end_at: toLocalInput(product.sales_end_at),
    requires_ticket: Boolean(product.requires_ticket),
    requires_vip: Boolean(product.requires_vip),
    max_per_buyer:
      product.max_per_buyer != null ? String(product.max_per_buyer) : "",
    show_on_event_page: product.show_on_event_page !== false,
    is_featured: Boolean(product.is_featured),
    pickup_enabled: product.pickup_enabled !== false,
    shipping_enabled: Boolean(product.shipping_enabled),
    print_on_demand_enabled: Boolean(product.print_on_demand_enabled),
    pickup_instructions: product.pickup_instructions ?? "",
    pickup_location_label: product.pickup_location_label ?? "",
    pickup_time_window: product.pickup_time_window ?? "",
    fulfillment_notes: product.fulfillment_notes ?? "",
    restock_on_refund: product.restock_on_refund,
    size_chart_id: product.size_chart_id ?? "",
    is_sponsor_branded: Boolean(product.is_sponsor_branded),
    sponsor_brand_name: product.sponsor_brand_name ?? "",
    sponsor_logo_url: product.sponsor_logo_url ?? "",
    sponsor_description: product.sponsor_description ?? "",
    sponsor_split_type: product.sponsor_split_type ?? "",
    sponsor_split_value:
      product.sponsor_split_value != null
        ? String(product.sponsor_split_value)
        : "",
    is_vault_exclusive: Boolean(
      product.is_vault_exclusive || product.requires_vault_access,
    ),
    required_access_type: product.required_access_type ?? "",
    required_vault_item_id: product.required_vault_item_id ?? "",
    requires_check_in: Boolean(product.requires_check_in),
    storefront_visibility: product.storefront_visibility || "event_only",
    variants,
  };
}

function variantToBody(v: MerchVariantFormRow): MerchVariantWriteBody {
  return {
    label: v.label.trim() || "Default",
    size: v.size.trim() || null,
    color: v.color.trim() || null,
    option_1_name: v.option_1_name.trim() || null,
    option_1_value: v.option_1_value.trim() || null,
    option_2_name: v.option_2_name.trim() || null,
    option_2_value: v.option_2_value.trim() || null,
    sku: v.sku.trim() || null,
    price_override: v.price_override.trim() ? Number(v.price_override) : null,
    inventory_count: Math.max(0, Number(v.inventory) || 0),
    status: v.status || "active",
    print_on_demand_variant_ref: v.print_on_demand_variant_ref.trim() || null,
  };
}

export function HostMerchProductForm({
  eventId,
  product,
  eventOptions,
  submitLabel,
  onSaved,
  studio = true,
  allowStandalone = false,
}: {
  eventId?: string;
  product?: MerchProduct | null;
  eventOptions?: { id: string; title: string }[];
  submitLabel?: string;
  onSaved: (product: MerchProduct) => void;
  studio?: boolean;
  /** Allow creating without an event (standalone host shop product). */
  allowStandalone?: boolean;
}) {
  const previewRef = useRef<HTMLDivElement | null>(null);
  const [values, setValues] = useState<MerchProductFormValues>(
    product ? productToFormValues(product) : DEFAULT_MERCH_FORM_VALUES,
  );
  const [selectedEventId, setSelectedEventId] = useState(
    eventId ?? product?.event_id ?? eventOptions?.[0]?.id ?? "",
  );
  const [section, setSection] = useState<MerchFormSectionId>("basics");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [sizeCharts, setSizeCharts] = useState<MerchSizeChart[]>([]);
  const [vaultItems, setVaultItems] = useState<VaultItem[]>([]);
  const [openVault, setOpenVault] = useState(Boolean(product?.is_vault_exclusive));
  const [openSponsor, setOpenSponsor] = useState(
    Boolean(product?.is_sponsor_branded),
  );
  const [openTicket, setOpenTicket] = useState(
    Boolean(product?.requires_ticket || product?.requires_check_in),
  );

  useEffect(() => {
    let active = true;
    void fetchHostSizeCharts()
      .then((charts) => {
        if (active) setSizeCharts(charts);
      })
      .catch(() => {
        if (active) setSizeCharts([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    void fetchHostVaultItems()
      .then((items) => {
        if (active) setVaultItems(items);
      })
      .catch(() => {
        if (active) setVaultItems([]);
      });
    return () => {
      active = false;
    };
  }, []);

  function setField<K extends keyof MerchProductFormValues>(
    key: K,
    value: MerchProductFormValues[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  const eventTitle =
    eventOptions?.find((e) => e.id === (eventId ?? selectedEventId))?.title ||
    product?.event_title ||
    null;

  const eventSelected = Boolean(eventId || selectedEventId);
  const isStandalone = allowStandalone && !eventSelected;
  const checklist = useMemo(
    () =>
      buildPublishChecklist(values, eventSelected, {
        requireEvent: !allowStandalone,
      }),
    [values, eventSelected, allowStandalone],
  );

  const sectionStatuses = useMemo((): Record<
    MerchFormSectionId,
    MerchSectionStatus
  > => {
    const salesEndBeforeStart =
      values.sales_start_at &&
      values.sales_end_at &&
      new Date(values.sales_end_at) < new Date(values.sales_start_at);
    const basicsDone = Boolean(
      values.name.trim() && (eventSelected || allowStandalone),
    );
    return {
      basics: basicsDone ? "complete" : "needs_info",
      media:
        values.cover_image_url.trim() || values.use_fallback_visual
          ? "complete"
          : "optional",
      pricing:
        values.base_price.trim() !== "" &&
        values.variants.length > 0 &&
        values.variants.every((v) => Number(v.inventory) >= 0)
          ? "complete"
          : "needs_info",
      sales: salesEndBeforeStart ? "needs_info" : "optional",
      access: "optional",
      fulfillment:
        values.pickup_enabled ||
        values.shipping_enabled ||
        values.print_on_demand_enabled
          ? "complete"
          : "needs_info",
      review: checklist.every((c) => c.done) ? "complete" : "needs_info",
    };
  }, [checklist, eventSelected, allowStandalone, values]);

  function validate(mode: "draft" | "publish"): Record<string, string> {
    const errors: Record<string, string> = {};
    if (!allowStandalone && !eventSelected) {
      errors.event = "Event is required";
    }
    if (!values.name.trim()) errors.name = "Product name is required";
    // Backend always requires a fulfillment channel.
    if (
      !values.pickup_enabled &&
      !values.shipping_enabled &&
      !values.print_on_demand_enabled
    ) {
      errors.fulfillment = "Select at least one fulfillment option";
    }
    for (const v of values.variants) {
      if (Number(v.inventory) < 0) {
        errors[`variant_${v.key}_inventory`] = "Inventory cannot be negative";
      }
    }

    if (mode === "publish") {
      if (values.base_price.trim() === "" || Number(values.base_price) < 0) {
        errors.base_price = "Base price is required";
      }
      if (values.variants.length === 0) {
        errors.variants = "At least one variant is required";
      }
      for (const v of values.variants) {
        if (v.price_override.trim() && Number(v.price_override) < 0) {
          errors[`variant_${v.key}_price`] = "Price override cannot be negative";
        }
      }
      if (
        values.sales_start_at &&
        values.sales_end_at &&
        new Date(values.sales_end_at) < new Date(values.sales_start_at)
      ) {
        errors.sales_end_at = "Sales end must be after sales start";
      }
      if (
        values.is_vault_exclusive &&
        values.required_access_type === "invite_only" &&
        !values.required_vault_item_id
      ) {
        errors.required_vault_item_id =
          "Vault-exclusive invite-only products need a linked Vault item";
      }
      if (values.is_sponsor_branded && !values.sponsor_brand_name.trim()) {
        errors.sponsor_brand_name =
          "Sponsor-branded products require a sponsor name";
      }
      if (
        values.is_sponsor_branded &&
        values.sponsor_split_type &&
        !values.sponsor_split_value.trim()
      ) {
        errors.sponsor_split_value =
          "Enter a sponsor split value, or clear the split type";
      }
      if (
        values.storefront_visibility === "hidden" &&
        !values.show_on_event_page
      ) {
        errors.storefront_visibility =
          "Product is hidden from all public surfaces";
      }
    }

    return errors;
  }

  function buildBody(): MerchProductWriteBody {
    const cover = values.use_fallback_visual
      ? null
      : values.cover_image_url.trim() || null;

    return {
      name: values.name.trim(),
      description: values.description.trim() || null,
      short_description: values.short_description.trim() || null,
      product_type: values.product_type || null,
      category: values.category.trim() || null,
      tags: values.tags
        .map((t) => t.trim())
        .filter(Boolean)
        .slice(0, 20),
      base_price: Number(values.base_price) || 0,
      currency: values.currency || "NGN",
      cover_image_url: cover,
      gallery_urls: parseGallery(values.gallery_urls),
      status: values.status,
      sales_start_at: fromLocalInput(values.sales_start_at),
      sales_end_at: fromLocalInput(values.sales_end_at),
      requires_ticket: values.requires_ticket,
      max_per_buyer: values.max_per_buyer.trim()
        ? Math.max(1, Number(values.max_per_buyer) || 1)
        : null,
      show_on_event_page: values.show_on_event_page,
      is_featured: values.is_featured,
      pickup_enabled: values.pickup_enabled,
      shipping_enabled: values.shipping_enabled,
      print_on_demand_enabled: values.print_on_demand_enabled,
      pickup_instructions: values.pickup_instructions.trim() || null,
      pickup_location_label: values.pickup_location_label.trim() || null,
      pickup_time_window: values.pickup_time_window.trim() || null,
      fulfillment_notes: values.fulfillment_notes.trim() || null,
      restock_on_refund: values.restock_on_refund,
      size_chart_id: values.size_chart_id.trim() || null,
      is_sponsor_branded: values.is_sponsor_branded,
      sponsor_brand_name: values.is_sponsor_branded
        ? values.sponsor_brand_name.trim() || null
        : null,
      sponsor_logo_url: values.is_sponsor_branded
        ? values.sponsor_logo_url.trim() || null
        : null,
      sponsor_description: values.is_sponsor_branded
        ? values.sponsor_description.trim() || null
        : null,
      sponsor_split_type: values.is_sponsor_branded
        ? values.sponsor_split_type || null
        : null,
      sponsor_split_value:
        values.is_sponsor_branded && values.sponsor_split_value.trim()
          ? Number(values.sponsor_split_value)
          : null,
      is_vault_exclusive: values.is_vault_exclusive,
      requires_vault_access: values.is_vault_exclusive,
      required_access_type: values.is_vault_exclusive
        ? values.required_access_type.trim() || null
        : null,
      required_vault_item_id: values.is_vault_exclusive
        ? values.required_vault_item_id.trim() || null
        : null,
      requires_check_in:
        values.requires_check_in ||
        values.required_access_type === "checked_in_attendee",
      storefront_visibility: values.is_vault_exclusive
        ? values.storefront_visibility === "event_only"
          ? "vault_exclusive"
          : values.storefront_visibility
        : values.storefront_visibility || "event_only",
    };
  }

  async function persist(mode: "draft" | "publish") {
    const nextStatus =
      mode === "draft"
        ? "draft"
        : values.status === "paused"
          ? "paused"
          : "active";
    const working = { ...values, status: nextStatus };
    setValues(working);

    const errors = validate(mode);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      const first = Object.values(errors)[0];
      setError(first);
      if (errors.name || errors.event) setSection("basics");
      else if (errors.base_price || errors.variants) setSection("pricing");
      else if (errors.sales_end_at) setSection("sales");
      else if (errors.sponsor_brand_name || errors.required_vault_item_id)
        setSection("access");
      else if (errors.fulfillment) setSection("fulfillment");
      else setSection("review");
      return;
    }

    const targetEventId = eventId ?? selectedEventId;
    setSaving(true);
    setError(null);
    try {
      const body = {
        ...buildBody(),
        status: nextStatus,
        ...(isStandalone || !targetEventId
          ? {
              marketplace_kind: "standalone",
              storefront_visibility:
                values.storefront_visibility === "event_only"
                  ? "host_storefront"
                  : values.storefront_visibility || "host_storefront",
              marketplace_listed: true,
            }
          : {}),
      };
      const variantBodies = working.variants.map(variantToBody);

      if (product) {
        const updated = await updateMerchProduct(
          product.id,
          body,
          targetEventId || undefined,
        );
        for (const variant of working.variants) {
          const vBody = variantToBody(variant);
          if (variant.id) {
            await updateMerchVariant(variant.id, vBody);
          } else {
            await createMerchVariant(product.id, vBody);
          }
        }
        onSaved(updated);
      } else if (targetEventId) {
        const created = await createMerchProduct(targetEventId, {
          ...body,
          variants: variantBodies,
        });
        onSaved(created);
      } else {
        const created = await createStandaloneMerchProduct({
          ...body,
          variants: variantBodies,
        });
        onSaved(created);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save product");
    } finally {
      setSaving(false);
    }
  }

  const isDraft = values.status === "draft" || !product;
  const primaryLabel =
    submitLabel ||
    (product
      ? "Save product"
      : isDraft && values.status === "draft"
        ? "Save product"
        : "Create product");
  const publishLabel = product
    ? values.status === "active"
      ? "Publish product"
      : "Save product"
    : values.status === "active"
      ? "Create product"
      : "Publish product";

  const canPublish = checklist.every((c) => c.done);

  const shortLen = values.short_description.length;

  const statusTone =
    values.status === "active"
      ? "success"
      : values.status === "paused"
        ? "warning"
        : values.status === "sold_out"
          ? "danger"
          : "neutral";

  const formSections = (
    <>
      {section === "basics" ? (
        <SectionShell
          title="Basics"
          description="Choose where this merch will appear and how fans can collect it."
        >
          {!eventId && (allowStandalone || (eventOptions && eventOptions.length > 0)) ? (
            <label className="block space-y-1.5 text-sm">
              <span className="font-bold text-foreground">
                {allowStandalone ? "Shop context" : "Event"}
              </span>
              <select
                className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                value={selectedEventId}
                onChange={(e) => {
                  const next = e.target.value;
                  setSelectedEventId(next);
                  if (!next && allowStandalone) {
                    setField("storefront_visibility", "host_storefront");
                  }
                }}
                disabled={Boolean(product)}
              >
                {allowStandalone ? (
                  <option value="">Standalone shop product</option>
                ) : null}
                {(eventOptions ?? []).map((event) => (
                  <option key={event.id} value={event.id}>
                    {event.title}
                  </option>
                ))}
              </select>
              {allowStandalone && !selectedEventId ? (
                <FieldHint>
                  Lists on your host shop and the Pàdéyá merch marketplace — no
                  event required.
                </FieldHint>
              ) : null}
              {fieldErrors.event ? (
                <p className="text-xs font-medium text-danger">
                  {fieldErrors.event}
                </p>
              ) : null}
            </label>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <Input
                label="Product name"
                value={values.name}
                onChange={(e) => setField("name", e.target.value)}
                placeholder="Official tee"
                error={fieldErrors.name}
              />
              <MerchTitleAI
                values={values}
                eventId={selectedEventId || eventId}
                merchProductId={product?.id}
                eventTitle={eventTitle}
                onApplyTitle={(title) => setField("name", title)}
              />
            </div>
            <label className="block space-y-1.5 text-sm">
              <span className="font-bold text-foreground">Product type</span>
              <select
                className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                value={values.product_type}
                onChange={(e) => setField("product_type", e.target.value)}
              >
                {MERCH_PRODUCT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="space-y-1.5">
            <Input
              label="Short description"
              value={values.short_description}
              onChange={(e) =>
                setField("short_description", e.target.value.slice(0, 280))
              }
              placeholder="Soft cotton event tee"
            />
            <p className="text-xs text-muted-foreground">{shortLen}/280</p>
          </div>

          <div className="space-y-2">
            <Textarea
              label="Full description"
              rows={5}
              value={values.description}
              onChange={(e) => setField("description", e.target.value)}
            />
            <MerchDescriptionAI
              values={values}
              eventId={selectedEventId || eventId}
              merchProductId={product?.id}
              eventTitle={eventTitle}
              onApplyDescription={(description) =>
                setField("description", description)
              }
            />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <label className="block space-y-1.5 text-sm">
              <span className="font-bold text-foreground">Browse category</span>
              <select
                className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                value={values.category}
                onChange={(e) => setField("category", e.target.value)}
              >
                <option value="">Select category</option>
                {MERCH_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
              <FieldHint>
                Controlled Pàdéyá marketplace categories only — AI can suggest,
                not invent.
              </FieldHint>
            </label>
            <div className="space-y-1.5">
              <Input
                label="Tags"
                value={values.tags.join(", ")}
                onChange={(e) =>
                  setField(
                    "tags",
                    e.target.value
                      .split(",")
                      .map((t) => t.trim())
                      .filter(Boolean)
                      .slice(0, 20),
                  )
                }
                placeholder="afrobeats, night out, tee"
              />
              <FieldHint>Comma-separated. Host can edit after AI apply.</FieldHint>
            </div>
          </div>

          <MerchCategoryTagAI
            values={values}
            eventId={selectedEventId || eventId}
            merchProductId={product?.id}
            eventTitle={eventTitle}
            onApplyCategory={(slug) => setField("category", slug)}
            onApplyTags={(tags) => setField("tags", tags.slice(0, 20))}
          />

          <div className="grid gap-3 md:grid-cols-2">
            <label className="block space-y-1.5 text-sm">
              <span className="font-bold text-foreground">Status</span>
              <select
                className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                value={values.status}
                onChange={(e) => setField("status", e.target.value)}
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="sold_out">Sold out</option>
              </select>
            </label>
            <label className="block space-y-1.5 text-sm">
              <span className="font-bold text-foreground">Size chart</span>
              <select
                className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                value={values.size_chart_id}
                onChange={(e) => setField("size_chart_id", e.target.value)}
              >
                <option value="">None</option>
                {sizeCharts.map((chart) => (
                  <option key={chart.id} value={chart.id}>
                    {chart.name}
                    {chart.status !== "active" ? ` (${chart.status})` : ""}
                  </option>
                ))}
              </select>
              <FieldHint>
                <Link
                  href="/host/merchandise/size-charts"
                  className="font-semibold text-foreground underline-offset-2 hover:underline"
                >
                  Manage size charts
                </Link>
              </FieldHint>
            </label>
          </div>
        </SectionShell>
      ) : null}

      {section === "media" ? (
        <SectionShell
          title="Media"
          description="Add a cover image or use a polished Pàdéyá fallback visual."
        >
          <div className="overflow-hidden rounded-[var(--radius-md)] border border-border">
            <div className="aspect-[2/1] max-h-56 bg-surface-muted sm:aspect-[16/10] sm:max-h-none">
              {!values.use_fallback_visual && values.cover_image_url.trim() ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={values.cover_image_url.trim()}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                <MerchFallbackVisual
                  productType={values.product_type}
                  productName={values.name}
                  eventTitle={eventTitle}
                />
              )}
            </div>
          </div>

          <ImageUrlOrUploadField
            label="Cover image"
            hint="Upload a product photo or paste a URL. Disable fallback visual to use your image."
            value={values.cover_image_url}
            onChange={(url) => {
              setField("cover_image_url", url);
              if (url.trim()) setField("use_fallback_visual", false);
            }}
            eventId={selectedEventId || eventId}
            mediaType="other"
            disabled={values.use_fallback_visual}
            previewClassName="h-14 w-20"
            previewContain
          />
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={values.use_fallback_visual}
              onChange={(e) => setField("use_fallback_visual", e.target.checked)}
            />
            Use fallback visual
          </label>

          <ImageUrlListUploadField
            label="Gallery images"
            hint="Upload one image at a time or paste URLs below."
            value={values.gallery_urls}
            onChange={(next) => setField("gallery_urls", next)}
            eventId={selectedEventId || eventId}
            mediaType="gallery"
          />
        </SectionShell>
      ) : null}

      {section === "pricing" ? (
        <SectionShell
          title="Pricing & variants"
          description="Set a base price, then add sizes, colors, and stock per variant."
        >
          <MerchVariantsEditor
            values={values}
            onChange={(variants) => setField("variants", variants)}
            onBasePriceChange={(v) => setField("base_price", v)}
            fieldErrors={fieldErrors}
          />
        </SectionShell>
      ) : null}

      {section === "sales" ? (
        <SectionShell
          title="Sales rules"
          description="Control when this product can be sold and where it appears."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Sales start"
              type="datetime-local"
              value={values.sales_start_at}
              onChange={(e) => setField("sales_start_at", e.target.value)}
            />
            <Input
              label="Sales end"
              type="datetime-local"
              value={values.sales_end_at}
              onChange={(e) => setField("sales_end_at", e.target.value)}
              error={fieldErrors.sales_end_at}
            />
          </div>
          {fieldErrors.sales_end_at ? null : values.sales_start_at &&
            values.sales_end_at &&
            new Date(values.sales_end_at) < new Date(values.sales_start_at) ? (
            <p className="text-sm font-medium text-warning-foreground">
              Sales end is before sales start.
            </p>
          ) : null}
          <Input
            label="Max quantity per buyer"
            type="number"
            min={1}
            value={values.max_per_buyer}
            onChange={(e) => setField("max_per_buyer", e.target.value)}
            placeholder="Optional"
          />
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={values.show_on_event_page}
              onChange={(e) => setField("show_on_event_page", e.target.checked)}
            />
            Show on event page
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={values.is_featured}
              onChange={(e) => setField("is_featured", e.target.checked)}
            />
            Featured on event page
          </label>
          <label className="block space-y-1.5 text-sm">
            <span className="font-bold text-foreground">Storefront visibility</span>
            <select
              className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
              value={values.storefront_visibility}
              onChange={(e) => setField("storefront_visibility", e.target.value)}
            >
              {STOREFRONT_VISIBILITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {fieldErrors.storefront_visibility ? (
              <p className="text-xs font-medium text-warning-foreground">
                {fieldErrors.storefront_visibility}
              </p>
            ) : null}
          </label>
        </SectionShell>
      ) : null}

      {section === "access" ? (
        <SectionShell
          title="Access"
          description="Public, ticket-holder, Vault, and sponsor rules."
        >
          <Expandable
            title="Ticket-holder rules"
            open={openTicket}
            onToggle={() => setOpenTicket((v) => !v)}
          >
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={values.requires_ticket}
                onChange={(e) => setField("requires_ticket", e.target.checked)}
              />
              Requires ticket in the same order
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={values.requires_check_in}
                onChange={(e) => setField("requires_check_in", e.target.checked)}
              />
              Requires checked-in attendee
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={
                  values.requires_vip ||
                  values.required_access_type === "vip_ticket_holder"
                }
                onChange={(e) => {
                  setField("requires_vip", e.target.checked);
                  if (e.target.checked) {
                    setField("required_access_type", "vip_ticket_holder");
                  }
                }}
              />
              Requires VIP ticket
            </label>
          </Expandable>

          <Expandable
            title="Vault settings"
            open={openVault}
            onToggle={() => setOpenVault((v) => !v)}
          >
            <FieldHint>
              Vault-exclusive merch shows a teaser when locked. Locked buyers
              never see private Vault details.
            </FieldHint>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={values.is_vault_exclusive}
                onChange={(e) => {
                  const on = e.target.checked;
                  setField("is_vault_exclusive", on);
                  if (on && values.storefront_visibility === "event_only") {
                    setField("storefront_visibility", "vault_exclusive");
                  }
                }}
              />
              Vault-exclusive merch
            </label>
            {values.is_vault_exclusive ? (
              <>
                <label className="block space-y-1.5 text-sm">
                  <span className="font-bold text-foreground">
                    Required access type
                  </span>
                  <select
                    className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                    value={values.required_access_type}
                    onChange={(e) =>
                      setField("required_access_type", e.target.value)
                    }
                  >
                    {ACCESS_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value || "any"} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block space-y-1.5 text-sm">
                  <span className="font-bold text-foreground">
                    Required Vault item
                  </span>
                  <select
                    className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                    value={values.required_vault_item_id}
                    onChange={(e) =>
                      setField("required_vault_item_id", e.target.value)
                    }
                  >
                    <option value="">Any qualifying Vault unlock</option>
                    {vaultItems.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title || item.slug || item.id}
                      </option>
                    ))}
                  </select>
                  {fieldErrors.required_vault_item_id ? (
                    <p className="text-xs font-medium text-danger">
                      {fieldErrors.required_vault_item_id}
                    </p>
                  ) : null}
                </label>
              </>
            ) : null}
          </Expandable>

          <Expandable
            title="Sponsor settings"
            open={openSponsor}
            onToggle={() => setOpenSponsor((v) => !v)}
          >
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={values.is_sponsor_branded}
                onChange={(e) => setField("is_sponsor_branded", e.target.checked)}
              />
              Sponsor-branded product
            </label>
            {values.is_sponsor_branded ? (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <Input
                    label="Sponsor name"
                    value={values.sponsor_brand_name}
                    onChange={(e) =>
                      setField("sponsor_brand_name", e.target.value)
                    }
                    error={fieldErrors.sponsor_brand_name}
                  />
                  <ImageUrlOrUploadField
                    label="Sponsor logo"
                    value={values.sponsor_logo_url}
                    onChange={(url) => setField("sponsor_logo_url", url)}
                    eventId={selectedEventId || eventId}
                    mediaType="sponsor"
                    previewContain
                    previewClassName="h-12 w-20"
                  />
                </div>
                <Textarea
                  label="Sponsor description"
                  rows={2}
                  value={values.sponsor_description}
                  onChange={(e) =>
                    setField("sponsor_description", e.target.value)
                  }
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block space-y-1.5 text-sm">
                    <span className="font-bold text-foreground">Split type</span>
                    <select
                      className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                      value={values.sponsor_split_type}
                      onChange={(e) =>
                        setField("sponsor_split_type", e.target.value)
                      }
                    >
                      <option value="">None</option>
                      <option value="percent">Percent of gross</option>
                      <option value="fixed">Fixed amount</option>
                    </select>
                  </label>
                  <Input
                    label="Split value"
                    type="number"
                    min={0}
                    value={values.sponsor_split_value}
                    onChange={(e) =>
                      setField("sponsor_split_value", e.target.value)
                    }
                    disabled={!values.sponsor_split_type}
                    error={fieldErrors.sponsor_split_value}
                  />
                </div>
              </>
            ) : null}
          </Expandable>
        </SectionShell>
      ) : null}

      {section === "fulfillment" ? (
        <SectionShell
          title="Fulfillment"
          description="Buyer addresses are encrypted and private on Pàdéyá. Public pickup copy must not reveal hidden venue details."
        >
          {fieldErrors.fulfillment ? (
            <p className="text-sm font-medium text-danger">
              {fieldErrors.fulfillment}
            </p>
          ) : null}
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={values.pickup_enabled}
              onChange={(e) => setField("pickup_enabled", e.target.checked)}
            />
            Pickup at event
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={values.shipping_enabled}
              onChange={(e) => setField("shipping_enabled", e.target.checked)}
            />
            Shipping / delivery
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={values.print_on_demand_enabled}
              onChange={(e) =>
                setField("print_on_demand_enabled", e.target.checked)
              }
            />
            Print on demand
          </label>

          {values.shipping_enabled ? (
            <FieldHint>
              Addresses stay encrypted and private.{" "}
              <Link
                href="/host/merchandise/shipping-zones"
                className="font-semibold text-foreground underline-offset-2 hover:underline"
              >
                Manage shipping zones
              </Link>
            </FieldHint>
          ) : null}

          {values.pickup_enabled ? (
            <div className="space-y-3">
              <Input
                label="Pickup location label"
                value={values.pickup_location_label}
                onChange={(e) =>
                  setField("pickup_location_label", e.target.value)
                }
              />
              <Input
                label="Pickup time window"
                value={values.pickup_time_window}
                onChange={(e) => setField("pickup_time_window", e.target.value)}
              />
              <Textarea
                label="Pickup instructions"
                rows={2}
                value={values.pickup_instructions}
                onChange={(e) =>
                  setField("pickup_instructions", e.target.value)
                }
              />
            </div>
          ) : null}

          {values.print_on_demand_enabled ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block space-y-1.5 text-sm">
                <span className="font-bold text-foreground">POD provider</span>
                <select
                  className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                  value={values.pod_provider}
                  onChange={(e) => setField("pod_provider", e.target.value)}
                >
                  <option value="manual">Manual</option>
                  <option value="printful">Printful (placeholder)</option>
                  <option value="printify">Printify (placeholder)</option>
                  <option value="custom">Custom</option>
                </select>
                <FieldHint>
                  Live provider sync is future — jobs are created after verified
                  payment for manual fulfillment.
                </FieldHint>
              </label>
              <Input
                label="Provider product ref"
                value={values.pod_product_ref}
                onChange={(e) => setField("pod_product_ref", e.target.value)}
              />
              <Input
                label="Provider variant ref"
                value={
                  values.variants[0]?.print_on_demand_variant_ref ?? ""
                }
                onChange={(e) => {
                  const first = values.variants[0];
                  if (!first) return;
                  setField(
                    "variants",
                    values.variants.map((v, i) =>
                      i === 0
                        ? {
                            ...v,
                            print_on_demand_variant_ref: e.target.value,
                          }
                        : v,
                    ),
                  );
                }}
              />
            </div>
          ) : null}

          <Textarea
            label="Fulfillment notes (staff)"
            rows={2}
            value={values.fulfillment_notes}
            onChange={(e) => setField("fulfillment_notes", e.target.value)}
          />
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={values.restock_on_refund}
              onChange={(e) => setField("restock_on_refund", e.target.checked)}
            />
            Restock inventory when an unfulfilled order is refunded
          </label>
        </SectionShell>
      ) : null}

      {section === "review" ? (
        <SectionShell
          title="Review & publish"
          description="Confirm details, then save as draft or publish to fans."
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={statusTone} size="sm">
              {values.status}
            </Badge>
            <Badge tone="outline" size="sm">
              {values.product_type.replaceAll("_", " ")}
            </Badge>
            {eventTitle ? (
              <Badge tone="outline" size="sm">
                {eventTitle}
              </Badge>
            ) : null}
          </div>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">Name</dt>
              <dd className="font-bold text-foreground">
                {values.name || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Base price</dt>
              <dd className="font-bold text-foreground">
                ₦{values.base_price || "0"}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Variants</dt>
              <dd className="font-bold text-foreground">
                {values.variants.length}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Fulfillment</dt>
              <dd className="font-bold text-foreground">
                {[
                  values.pickup_enabled ? "Pickup" : null,
                  values.shipping_enabled ? "Shipping" : null,
                  values.print_on_demand_enabled ? "POD" : null,
                ]
                  .filter(Boolean)
                  .join(" · ") || "None"}
              </dd>
            </div>
          </dl>
          <MerchPublishChecklist items={checklist} />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => void persist("draft")}
              disabled={saving}
            >
              Save draft
            </Button>
            <Button
              type="button"
              onClick={() => void persist("publish")}
              disabled={saving || !canPublish}
            >
              {publishLabel}
            </Button>
          </div>
        </SectionShell>
      ) : null}
    </>
  );

  if (!studio) {
    return (
      <div className="space-y-6 pb-24">
        {formSections}
        {error ? (
          <p className="text-sm font-medium text-danger">{error}</p>
        ) : null}
        <Button disabled={saving} onClick={() => void persist("publish")}>
          {saving ? "Saving…" : primaryLabel}
        </Button>
      </div>
    );
  }

  const stepIndex = MERCH_FORM_SECTIONS.findIndex((s) => s.id === section);

  return (
    <div className="space-y-4 pb-28 md:pb-10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge tone={statusTone} size="sm">
            {values.status}
          </Badge>
          <p className="text-sm text-muted-foreground">
            Merch Studio
            <span className="mx-1.5 text-border">·</span>
            Step {stepIndex + 1} of {MERCH_FORM_SECTIONS.length}
          </p>
        </div>
        <div className="hidden flex-wrap items-center gap-2 md:flex">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              setSection("review");
              previewRef.current?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              });
            }}
          >
            Preview
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={saving}
            onClick={() => void persist("draft")}
          >
            {saving ? "Saving…" : "Save draft"}
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={saving || !canPublish}
            onClick={() => void persist("publish")}
          >
            {saving ? "Saving…" : publishLabel}
          </Button>
        </div>
      </div>

      <MerchFormStepper
        active={section}
        onChange={setSection}
        statuses={sectionStatuses}
      />

      <MerchStickyActions
        saving={saving}
        primaryLabel={publishLabel}
        draftLabel="Save draft"
        canPublish={canPublish}
        onSaveDraft={() => void persist("draft")}
        onPublish={() => void persist("publish")}
        onPreview={() => {
          setSection("review");
          previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }}
        desktopHidden
      />

      {error ? (
        <div className="rounded-[var(--radius-md)] border border-danger/40 bg-danger-surface px-4 py-3 text-sm font-medium text-danger-foreground">
          {error}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px] xl:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
        <div className="min-w-0 space-y-4">{formSections}</div>
        <aside
          ref={previewRef}
          className="space-y-4 lg:sticky lg:top-24 lg:self-start"
        >
          <HostMerchProductPreview values={values} eventTitle={eventTitle} />
          <MerchPublishChecklist items={checklist} className="hidden lg:block" />
          <div className="hidden gap-2 lg:flex">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1"
              onClick={() =>
                setSection((s) => {
                  const order: MerchFormSectionId[] = [
                    "basics",
                    "media",
                    "pricing",
                    "sales",
                    "access",
                    "fulfillment",
                    "review",
                  ];
                  const idx = order.indexOf(s);
                  return order[Math.max(0, idx - 1)] ?? s;
                })
              }
            >
              Back
            </Button>
            <Button
              type="button"
              size="sm"
              className="flex-1"
              onClick={() =>
                setSection((s) => {
                  const order: MerchFormSectionId[] = [
                    "basics",
                    "media",
                    "pricing",
                    "sales",
                    "access",
                    "fulfillment",
                    "review",
                  ];
                  const idx = order.indexOf(s);
                  return order[Math.min(order.length - 1, idx + 1)] ?? s;
                })
              }
            >
              Next
            </Button>
          </div>
        </aside>
      </div>
    </div>
  );
}

/** Alias for shared imports. */
export { HostMerchProductForm as MerchProductForm };
