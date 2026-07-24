"use client";

import { useEffect, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Input,
  PromoCodeCard,
  SectionHeader,
  Select,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyEvents, fetchTicketTypes } from "@/lib/events-api";
import { createPromo, fetchHostPromos, updatePromo } from "@/lib/promos-api";
import type { EventItem, TicketType } from "@/lib/types/events";
import type { PromoCode } from "@/lib/types/promos";

export default function HostPromosPage() {
  const [promos, setPromos] = useState<PromoCode[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [code, setCode] = useState("");
  const [discountType, setDiscountType] = useState("percentage");
  const [discountValue, setDiscountValue] = useState("10");
  const [usageLimit, setUsageLimit] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [eventId, setEventId] = useState("");
  const [ticketTypeId, setTicketTypeId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [promoRows, eventRows] = await Promise.all([
      fetchHostPromos(),
      fetchMyEvents(),
    ]);
    setPromos(promoRows);
    setEvents(eventRows);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load promos");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!eventId) return;
    let active = true;
    void fetchTicketTypes(eventId)
      .then((rows) => {
        if (active) setTicketTypes(rows);
      })
      .catch(() => {
        if (active) setTicketTypes([]);
      });
    return () => {
      active = false;
    };
  }, [eventId]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createPromo({
        code,
        discount_type: discountType,
        discount_value: Number(discountValue),
        usage_limit: usageLimit ? Number(usageLimit) : null,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        event_id: eventId || null,
        ticket_type_id: ticketTypeId || null,
      });
      setCode("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    }
  }

  async function toggleStatus(promo: PromoCode) {
    try {
      await updatePromo(promo.id, {
        status: promo.status === "active" ? "inactive" : "active",
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Promos"
        title="Promo codes"
        description="Percentage or fixed discounts with limits, expiry, and event/ticket restrictions."
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <Card className="mb-8 max-w-2xl space-y-4">
          <SectionHeader
            title="Create promo"
            description="Codes are case-sensitive and validated at checkout."
          />
          <form className="space-y-4" onSubmit={onCreate}>
            <Input
              label="Code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              hint="Short, memorable — e.g. EARLYBIRD"
              required
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Discount type"
                value={discountType}
                onChange={(e) => setDiscountType(e.target.value)}
              >
                <option value="percentage">Percentage</option>
                <option value="fixed">Fixed amount</option>
              </Select>
              <Input
                label={discountType === "percentage" ? "Percent" : "Amount (NGN)"}
                type="number"
                value={discountValue}
                onChange={(e) => setDiscountValue(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Usage limit (optional)"
                type="number"
                value={usageLimit}
                onChange={(e) => setUsageLimit(e.target.value)}
                hint="Leave blank for unlimited."
              />
              <Input
                label="Expires at (optional)"
                type="datetime-local"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
              />
            </div>
            <Select
              label="Event restriction"
              value={eventId}
              onChange={(e) => {
                setEventId(e.target.value);
                setTicketTypeId("");
                setTicketTypes([]);
              }}
              hint="Limit to a single event, or leave open."
            >
              <option value="">Any event</option>
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.title}
                </option>
              ))}
            </Select>
            <Select
              label="Ticket type restriction"
              value={ticketTypeId}
              onChange={(e) => setTicketTypeId(e.target.value)}
              disabled={!eventId}
              hint={!eventId ? "Select an event first." : undefined}
            >
              <option value="">Any ticket type</option>
              {ticketTypes.map((tt) => (
                <option key={tt.id} value={tt.id}>
                  {tt.name}
                </option>
              ))}
            </Select>
            <Button type="submit">Create promo</Button>
          </form>
        </Card>

        <div className="space-y-4">
          <SectionHeader
            title="Active codes"
            description={`${promos.length} promo${promos.length === 1 ? "" : "s"} in your account.`}
          />
          {promos.length === 0 ? (
            <EmptyState
              title="No promo codes yet"
              description="Create a code to reward early buyers or partners."
            />
          ) : (
            <div className="space-y-3">
              {promos.map((promo) => (
                <PromoCodeCard
                  key={promo.id}
                  promo={promo}
                  actions={
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void toggleStatus(promo)}
                    >
                      {promo.status === "active" ? "Deactivate" : "Activate"}
                    </Button>
                  }
                />
              ))}
            </div>
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
