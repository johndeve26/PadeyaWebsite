"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

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
import { fetchEventById } from "@/lib/events-api";
import {
  createHostPostEventDrop,
  fetchHostPostEventDrops,
  patchHostPostEventDrop,
} from "@/lib/merch-api";
import type { EventItem } from "@/lib/types/events";
import type { PostEventDrop, PostEventDropAudience } from "@/lib/types/merch";

const AUDIENCE_OPTIONS: { value: PostEventDropAudience; label: string }[] = [
  { value: "public", label: "Public" },
  { value: "ticket_buyers", label: "Ticket buyers" },
  { value: "checked_in", label: "Checked-in attendees" },
  { value: "vip", label: "VIP ticket holders" },
  { value: "vault_members", label: "Vault members" },
];

type FormState = {
  name: string;
  drop_description: string;
  audience: PostEventDropAudience;
  post_event_drop_at: string;
  base_price: string;
  inventory_count: string;
  status: string;
};

const EMPTY_FORM: FormState = {
  name: "",
  drop_description: "",
  audience: "ticket_buyers",
  post_event_drop_at: "",
  base_price: "",
  inventory_count: "50",
  status: "draft",
};

function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

function fromLocalInput(value: string): string | null {
  if (!value.trim()) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function eventEnded(event: EventItem | null): boolean {
  if (!event) return false;
  if (event.status === "completed") return true;
  if (event.status !== "published") return false;
  return new Date(event.end_datetime).getTime() <= Date.now();
}

function audienceLabel(value: string): string {
  return AUDIENCE_OPTIONS.find((o) => o.value === value)?.label || value;
}

export default function HostPostEventDropsPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [drops, setDrops] = useState<PostEventDrop[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [ev, rows] = await Promise.all([
      fetchEventById(params.id),
      fetchHostPostEventDrops(params.id),
    ]);
    setEvent(ev);
    setDrops(rows);
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
            err instanceof ApiError
              ? err.detail
              : "Failed to load post-event drops",
          );
          setDrops([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  function startEdit(drop: PostEventDrop) {
    setEditingId(drop.id);
    setForm({
      name: drop.name,
      drop_description: drop.drop_description || drop.short_description || "",
      audience: (drop.audience as PostEventDropAudience) || "public",
      post_event_drop_at: toLocalInput(drop.post_event_drop_at),
      base_price: String(drop.base_price ?? ""),
      inventory_count: String(drop.total_inventory ?? 0),
      status: drop.status || "draft",
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const price = Number(form.base_price);
      if (!form.name.trim() || Number.isNaN(price) || price < 0) {
        throw new Error("Name and a valid price are required");
      }
      if (editingId) {
        await patchHostPostEventDrop(params.id, editingId, {
          name: form.name.trim(),
          drop_description: form.drop_description.trim() || null,
          audience: form.audience,
          post_event_drop_at: fromLocalInput(form.post_event_drop_at),
          status: form.status,
          base_price: price,
        });
        toast.push({ tone: "success", title: "Drop updated" });
      } else {
        await createHostPostEventDrop(params.id, {
          name: form.name.trim(),
          base_price: price,
          audience: form.audience,
          drop_description: form.drop_description.trim() || null,
          post_event_drop_at: fromLocalInput(form.post_event_drop_at),
          status: form.status,
          inventory_count: Number(form.inventory_count) || 0,
        });
        toast.push({ tone: "success", title: "Post-event drop created" });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Could not save drop",
      );
    } finally {
      setSaving(false);
    }
  }

  async function activateDrop(drop: PostEventDrop) {
    setSaving(true);
    try {
      await patchHostPostEventDrop(params.id, drop.id, { status: "active" });
      toast.push({ tone: "success", title: "Drop activated" });
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not activate drop",
      );
    } finally {
      setSaving(false);
    }
  }

  const canCreate = eventEnded(event);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Post-event drops"
        description={
          event
            ? `Recap merch for ${event.title} on Pàdéyá — schedule release and pick who can buy.`
            : "Recap merch after the event ends."
        }
        actions={<EventOpsNav eventId={params.id} />}
      >
        <EventMerchSubnav eventId={params.id} />

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {!canCreate && event ? (
          <Alert tone="warning" title="Event still in progress">
            Create post-event drops after the event ends or is marked completed.
          </Alert>
        ) : null}

        <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_1.1fr]">
          <Card className="space-y-4 p-5">
            <div>
              <h2 className="text-lg font-extrabold tracking-tight">
                {editingId ? "Edit drop" : "New drop"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Limited souvenirs and recap merch for attendees.
              </p>
            </div>
            <form className="space-y-4" onSubmit={onSubmit}>
              <Input
                label="Drop name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
              <Textarea
                label="Drop description"
                value={form.drop_description}
                onChange={(e) =>
                  setForm((f) => ({ ...f, drop_description: e.target.value }))
                }
                rows={3}
              />
              <Select
                label="Audience"
                value={form.audience}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    audience: e.target.value as PostEventDropAudience,
                  }))
                }
              >
                {AUDIENCE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
              <Input
                label="Release at"
                type="datetime-local"
                value={form.post_event_drop_at}
                onChange={(e) =>
                  setForm((f) => ({ ...f, post_event_drop_at: e.target.value }))
                }
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Price (NGN)"
                  inputMode="decimal"
                  value={form.base_price}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, base_price: e.target.value }))
                  }
                  required
                />
                {!editingId ? (
                  <Input
                    label="Inventory"
                    inputMode="numeric"
                    value={form.inventory_count}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, inventory_count: e.target.value }))
                    }
                  />
                ) : null}
              </div>
              <Select
                label="Status"
                value={form.status}
                onChange={(e) =>
                  setForm((f) => ({ ...f, status: e.target.value }))
                }
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
              </Select>
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={saving || (!canCreate && !editingId)}>
                  {editingId ? "Save drop" : "Create drop"}
                </Button>
                {editingId ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={resetForm}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                ) : null}
              </div>
            </form>
          </Card>

          <div className="space-y-4">
            <h2 className="text-lg font-extrabold tracking-tight">Your drops</h2>
            {drops === null ? <SkeletonLoader /> : null}
            {drops && drops.length === 0 ? (
              <EmptyState
                title="No post-event drops yet"
                description="Create a recap merch drop for ticket holders or the public after the event."
              />
            ) : null}
            {drops?.map((drop) => (
              <Card key={drop.id} className="space-y-3 p-5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-extrabold">{drop.name}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {formatNgn(Number(drop.base_price))} ·{" "}
                      {audienceLabel(String(drop.audience))}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <Badge tone="neutral" size="sm">
                      {drop.status}
                    </Badge>
                    {drop.is_drop_live ? (
                      <Badge tone="success" size="sm">
                        Live
                      </Badge>
                    ) : (
                      <Badge tone="warning" size="sm">
                        Scheduled
                      </Badge>
                    )}
                    {drop.requires_vault_access ? (
                      <Badge tone="dark" size="sm">
                        Vault
                      </Badge>
                    ) : null}
                  </div>
                </div>
                {drop.drop_description || drop.short_description ? (
                  <p className="text-sm text-muted-foreground">
                    {drop.drop_description || drop.short_description}
                  </p>
                ) : null}
                {drop.post_event_drop_at ? (
                  <p className="text-xs text-muted-foreground">
                    Releases{" "}
                    {new Date(drop.post_event_drop_at).toLocaleString()}
                  </p>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => startEdit(drop)}
                    disabled={saving}
                  >
                    Edit
                  </Button>
                  {drop.status !== "active" ? (
                    <Button
                      size="sm"
                      onClick={() => void activateDrop(drop)}
                      disabled={saving}
                    >
                      Activate
                    </Button>
                  ) : null}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
