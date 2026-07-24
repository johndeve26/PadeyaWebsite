"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminSponsorshipSlots,
  moderateSponsorshipSlot,
} from "@/lib/sponsorships-api";
import { formatNgn } from "@/lib/format";
import type { SponsorshipSlot } from "@/lib/types/sponsorships";

export default function AdminSponsorshipsPage() {
  const [slots, setSlots] = useState<SponsorshipSlot[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [modFilter, setModFilter] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setSlots(await fetchAdminSponsorshipSlots());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchAdminSponsorshipSlots();
        if (active) setSlots(rows);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const modStatuses = useMemo(() => {
    const set = new Set(slots.map((s) => s.moderation_status));
    return Array.from(set).sort();
  }, [slots]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return slots.filter((slot) => {
      if (modFilter !== "all" && slot.moderation_status !== modFilter) return false;
      if (!q) return true;
      const haystack = [
        slot.title,
        slot.description,
        slot.host_username,
        slot.host_display_name,
        slot.slot_type_label,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [slots, search, modFilter]);

  async function onModerate(id: string, action: string) {
    setError(null);
    setBusyId(id);
    try {
      const itemNote = notes[id]?.trim();
      await moderateSponsorshipSlot(id, action, itemNote || undefined);
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      const labels: Record<string, string> = {
        flag: "flagged",
        approve: "approved",
        disable: "disabled",
        remove: "removed",
      };
      setNote(`Listing ${labels[action] ?? "updated"}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Moderation failed");
    } finally {
      setBusyId(null);
    }
  }

  function renderActions(slot: SponsorshipSlot) {
    const busy = busyId === slot.id;
    return (
      <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void onModerate(slot.id, "flag")}
        >
          Flag
        </Button>
        <Button
          size="sm"
          disabled={busy}
          onClick={() => void onModerate(slot.id, "approve")}
        >
          Approve
        </Button>
        <ConfirmAction
          label="Disable"
          title="Disable this listing?"
          description={`Disable “${slot.title}”. It will no longer appear in the marketplace.`}
          confirmLabel="Disable listing"
          tone="danger"
          disabled={busy}
          busy={busy}
          onConfirm={() => onModerate(slot.id, "disable")}
        />
        <ConfirmAction
          label="Remove"
          title="Remove this listing?"
          description={`Permanently remove “${slot.title}” from sponsorship moderation.`}
          confirmLabel="Remove listing"
          tone="danger"
          disabled={busy}
          busy={busy}
          onConfirm={() => onModerate(slot.id, "remove")}
        />
      </div>
    );
  }

  const columns = [
    {
      key: "title",
      header: "Listing",
      primary: true,
      cell: (slot: SponsorshipSlot) => (
        <div className="space-y-1">
          <p className="font-bold text-foreground">{slot.title}</p>
          <p className="text-sm text-muted-foreground">{slot.slot_type_label}</p>
        </div>
      ),
    },
    {
      key: "host",
      header: "Host",
      cell: (slot: SponsorshipSlot) => (
        <div className="space-y-1">
          <p className="font-semibold text-foreground">
            {slot.host_display_name || "—"}
          </p>
          <p className="text-sm text-muted-foreground">
            @{slot.host_username || "—"}
            {slot.host_verified ? " · verified" : ""}
          </p>
        </div>
      ),
    },
    {
      key: "price",
      header: "Price",
      cell: (slot: SponsorshipSlot) => (
        <span className="font-semibold">{formatNgn(slot.price)}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (slot: SponsorshipSlot) => (
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge status={slot.status} />
          <StatusBadge status={slot.moderation_status} />
        </div>
      ),
    },
    {
      key: "note",
      header: "Note",
      cell: (slot: SponsorshipSlot) => (
        <Textarea
          aria-label={`Moderation note for ${slot.title}`}
          hint="Optional · applied to next action on this row"
          value={notes[slot.id] ?? ""}
          onChange={(e) =>
            setNotes((prev) => ({ ...prev, [slot.id]: e.target.value }))
          }
          className="min-h-[64px] text-sm"
        />
      ),
    },
    {
      key: "actions",
      header: "Moderate",
      cell: (slot: SponsorshipSlot) => renderActions(slot),
    },
  ];

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Sponsorship moderation"
      description="Review marketplace listings for Pàdéyá. Flag, approve, disable, or remove packages — actions are audited."
      actions={
        <Link href="/admin">
          <Button variant="secondary">Admin home</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Updated">
          {note}
        </Alert>
      ) : null}

      {loading && !error ? <SkeletonLoader lines={5} /> : null}

      {!loading && slots.length > 0 ? (
        <FilterBar
          trailing={
            <span className="text-sm font-semibold text-foreground">
              {filtered.length} listing{filtered.length === 1 ? "" : "s"}
            </span>
          }
        >
          <Input
            label="Search"
            placeholder="Title, host, package type…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select
            label="Moderation status"
            value={modFilter}
            onChange={(e) => setModFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            {modStatuses.map((status) => (
              <option key={status} value={status}>
                {status.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </FilterBar>
      ) : null}

      {!loading && slots.length === 0 && !error ? (
        <EmptyState
          title="No sponsorship slots to moderate"
          description="When hosts publish packages, they appear here for review."
        />
      ) : !loading ? (
        <DataTable
          columns={columns}
          rows={filtered}
          rowKey={(row) => row.id}
          emptyTitle="No matching listings"
          emptyDescription="Try a different search or moderation filter."
          mobileCard={(slot) => (
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-foreground">{slot.title}</h3>
                <StatusBadge status={slot.status} />
                <StatusBadge status={slot.moderation_status} />
              </div>
              <p className="text-sm text-muted-foreground">
                @{slot.host_username}
                {slot.host_verified ? " · verified" : ""} · {formatNgn(slot.price)}
              </p>
              <p className="line-clamp-3 text-sm text-muted-foreground">{slot.description}</p>
              <Textarea
                label="Moderation note (optional)"
                value={notes[slot.id] ?? ""}
                onChange={(e) =>
                  setNotes((prev) => ({ ...prev, [slot.id]: e.target.value }))
                }
                className="min-h-[72px]"
              />
              {renderActions(slot)}
            </Card>
          )}
        />
      ) : null}
    </DashboardShell>
  );
}
