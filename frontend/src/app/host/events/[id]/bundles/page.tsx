"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { EventOpsNav } from "@/components/host/EventOpsNav";
import { EventMerchSubnav } from "@/components/merch/host/EventMerchSubnav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Select,
  SkeletonLoader,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { fetchEventById, fetchTicketTypes } from "@/lib/events-api";
import {
  archiveHostEventBundle,
  createHostEventBundle,
  fetchHostEventBundles,
  fetchHostMerchProducts,
  updateHostEventBundle,
} from "@/lib/merch-api";
import type { TicketType } from "@/lib/types/events";
import type { MerchBundle, MerchProduct } from "@/lib/types/merch";

const STATUS_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "archived", label: "Archived" },
];

type FormState = {
  name: string;
  description: string;
  ticket_type_id: string;
  variant_id: string;
  merch_quantity: string;
  bundle_price: string;
  currency: string;
  inventory_limit: string;
  max_per_buyer: string;
  sales_start_at: string;
  sales_end_at: string;
  status: string;
};

const EMPTY_FORM: FormState = {
  name: "",
  description: "",
  ticket_type_id: "",
  variant_id: "",
  merch_quantity: "1",
  bundle_price: "",
  currency: "NGN",
  inventory_limit: "",
  max_per_buyer: "",
  sales_start_at: "",
  sales_end_at: "",
  status: "draft",
};

function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInput(value: string): string | null {
  if (!value.trim()) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

export default function EventBundlesPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [bundles, setBundles] = useState<MerchBundle[] | null>(null);
  const [tickets, setTickets] = useState<TicketType[]>([]);
  const [products, setProducts] = useState<MerchProduct[]>([]);
  const [eventTitle, setEventTitle] = useState("Event bundles");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const variantOptions = useMemo(() => {
    const rows: { value: string; label: string; productId: string }[] = [];
    for (const product of products) {
      for (const variant of product.variants || []) {
        rows.push({
          value: variant.id,
          productId: product.id,
          label: `${product.name} · ${variant.label || "Standard"}`,
        });
      }
    }
    return rows;
  }, [products]);

  const load = useCallback(async () => {
    const [rows, ticketRows, productRows, event] = await Promise.all([
      fetchHostEventBundles(params.id),
      fetchTicketTypes(params.id),
      fetchHostMerchProducts(params.id),
      fetchEventById(params.id),
    ]);
    setBundles(rows);
    setTickets(ticketRows);
    setProducts(productRows);
    setEventTitle(event.title || "Event bundles");
    setForm((prev) => ({
      ...prev,
      ticket_type_id:
        prev.ticket_type_id ||
        ticketRows.find((t) => t.status === "active")?.id ||
        ticketRows[0]?.id ||
        "",
      variant_id:
        prev.variant_id ||
        productRows.flatMap((p) => p.variants || [])[0]?.id ||
        "",
    }));
  }, [params.id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load bundles",
          );
          setBundles([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  function resetForm() {
    setEditingId(null);
    setForm({
      ...EMPTY_FORM,
      ticket_type_id:
        tickets.find((t) => t.status === "active")?.id || tickets[0]?.id || "",
      variant_id: variantOptions[0]?.value || "",
    });
  }

  function startEdit(bundle: MerchBundle) {
    const rule = bundle.merch_variant_rules?.[0];
    setEditingId(bundle.id);
    setForm({
      name: bundle.name,
      description: bundle.description || "",
      ticket_type_id: bundle.ticket_type_id,
      variant_id: rule?.variant_id || "",
      merch_quantity: String(rule?.quantity || 1),
      bundle_price: String(bundle.bundle_price),
      currency: bundle.currency || "NGN",
      inventory_limit:
        bundle.inventory_limit == null ? "" : String(bundle.inventory_limit),
      max_per_buyer:
        bundle.max_per_buyer == null ? "" : String(bundle.max_per_buyer),
      sales_start_at: toLocalInput(bundle.sales_start_at),
      sales_end_at: toLocalInput(bundle.sales_end_at),
      status: bundle.status || "draft",
    });
  }

  async function onSave() {
    setSaving(true);
    setError(null);
    try {
      const variant = variantOptions.find((v) => v.value === form.variant_id);
      if (!form.name.trim() || !form.ticket_type_id || !variant) {
        setError("Name, ticket type, and merch variant are required");
        setSaving(false);
        return;
      }
      const body = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        ticket_type_id: form.ticket_type_id,
        merch_variant_rules: [
          {
            product_id: variant.productId,
            variant_id: variant.value,
            quantity: Math.max(1, Number.parseInt(form.merch_quantity, 10) || 1),
          },
        ],
        bundle_price: form.bundle_price,
        currency: form.currency || "NGN",
        inventory_limit: form.inventory_limit.trim()
          ? Number.parseInt(form.inventory_limit, 10)
          : null,
        max_per_buyer: form.max_per_buyer.trim()
          ? Number.parseInt(form.max_per_buyer, 10)
          : null,
        sales_start_at: fromLocalInput(form.sales_start_at),
        sales_end_at: fromLocalInput(form.sales_end_at),
        status: form.status,
      };
      if (editingId) {
        await updateHostEventBundle(params.id, editingId, body);
        toast.push({ tone: "success", title: "Bundle updated" });
      } else {
        await createHostEventBundle(params.id, body);
        toast.push({ tone: "success", title: "Bundle created" });
      }
      await load();
      resetForm();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save bundle");
    } finally {
      setSaving(false);
    }
  }

  async function onArchive(bundleId: string) {
    setError(null);
    try {
      await archiveHostEventBundle(params.id, bundleId);
      toast.push({ tone: "success", title: "Bundle archived" });
      await load();
      if (editingId === bundleId) resetForm();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not archive bundle",
      );
    }
  }

  async function onSetStatus(bundle: MerchBundle, status: string) {
    setError(null);
    try {
      await updateHostEventBundle(params.id, bundle.id, { status });
      toast.push({ tone: "success", title: `Bundle ${status}` });
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not update status",
      );
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title={eventTitle}
        description="Ticket + merch packs for checkout. Price is one bundle total; inventory and sales windows are enforced server-side."
        actions={<EventOpsNav eventId={params.id} />}
      >
        <EventMerchSubnav eventId={params.id} />

        {error ? (
          <Alert tone="danger" className="mb-4">
            {error}
          </Alert>
        ) : null}

        {bundles == null ? (
          <SkeletonLoader lines={6} />
        ) : (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,380px)]">
            <Card className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-lg font-extrabold tracking-tight text-foreground">
                  {editingId ? "Edit bundle" : "Create bundle"}
                </h2>
                <p className="text-sm text-muted-foreground">
                  Pair one ticket type with merch. Buyers see savings when the
                  pack is below component list price.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Name"
                  value={form.name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                  className="sm:col-span-2"
                />
                <Textarea
                  label="Description"
                  value={form.description}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  className="sm:col-span-2"
                />
                <Select
                  label="Ticket type"
                  value={form.ticket_type_id}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      ticket_type_id: e.target.value,
                    }))
                  }
                >
                  {tickets.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} · {formatNgn(t.price)}
                    </option>
                  ))}
                </Select>
                <Select
                  label="Merch variant"
                  value={form.variant_id}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, variant_id: e.target.value }))
                  }
                >
                  {variantOptions.map((v) => (
                    <option key={v.value} value={v.value}>
                      {v.label}
                    </option>
                  ))}
                </Select>
                <Input
                  label="Merch qty in pack"
                  type="number"
                  min={1}
                  value={form.merch_quantity}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      merch_quantity: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Bundle price"
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.bundle_price}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      bundle_price: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Currency"
                  value={form.currency}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, currency: e.target.value }))
                  }
                />
                <Input
                  label="Inventory limit"
                  hint="Leave blank for unlimited packs"
                  type="number"
                  min={1}
                  value={form.inventory_limit}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      inventory_limit: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Max per buyer"
                  type="number"
                  min={1}
                  value={form.max_per_buyer}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      max_per_buyer: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Sales start"
                  type="datetime-local"
                  value={form.sales_start_at}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      sales_start_at: e.target.value,
                    }))
                  }
                />
                <Input
                  label="Sales end"
                  type="datetime-local"
                  value={form.sales_end_at}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      sales_end_at: e.target.value,
                    }))
                  }
                />
                <Select
                  label="Status"
                  value={form.status}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, status: e.target.value }))
                  }
                >
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void onSave()} disabled={saving}>
                  {saving
                    ? "Saving…"
                    : editingId
                      ? "Save changes"
                      : "Create bundle"}
                </Button>
                {editingId ? (
                  <Button variant="secondary" onClick={resetForm}>
                    Cancel edit
                  </Button>
                ) : null}
              </div>
            </Card>

            <Card className="space-y-4">
              <h2 className="text-lg font-extrabold tracking-tight text-foreground">
                Bundles
              </h2>
              {bundles.length === 0 ? (
                <EmptyState
                  title="No bundles yet"
                  description="Create a ticket + merch pack to show it on checkout before individual tickets."
                />
              ) : (
                <ul className="space-y-4">
                  {bundles.map((bundle) => {
                    const savings = Number(bundle.savings || 0);
                    return (
                      <li
                        key={bundle.id}
                        className="space-y-2 border-b border-border pb-4 last:border-0 last:pb-0"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="space-y-1">
                            <p className="font-bold text-foreground">
                              {bundle.name}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {formatNgn(bundle.bundle_price)}
                              {savings > 0
                                ? ` · saves ${formatNgn(savings)}`
                                : ""}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {bundle.ticket_type_name || "Ticket"}
                              {(bundle.merch_variant_rules || [])
                                .map(
                                  (r) =>
                                    ` + ${r.quantity}× ${r.product_name || "merch"}`,
                                )
                                .join("")}
                            </p>
                          </div>
                          <Badge tone="outline">{bundle.status}</Badge>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => startEdit(bundle)}
                          >
                            Edit
                          </Button>
                          {bundle.status !== "active" ? (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() =>
                                void onSetStatus(bundle, "active")
                              }
                            >
                              Activate
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() =>
                                void onSetStatus(bundle, "paused")
                              }
                            >
                              Pause
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => void onArchive(bundle.id)}
                          >
                            Archive
                          </Button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </div>
        )}
      </DashboardShell>
    </RequireHost>
  );
}
