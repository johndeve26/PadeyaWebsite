"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
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
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  activateAdminReferralProgram,
  createAdminReferralProgram,
  enrollAdminReferralProgram,
  fetchAdminReferralPrograms,
  pauseAdminReferralProgram,
  type ReferralProgram,
} from "@/lib/promos-api";

export default function AdminReferralProgramsPage() {
  const [rows, setRows] = useState<ReferralProgram[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Create form
  const [name, setName] = useState("Pàdéyá Ambassadors");
  const [description, setDescription] = useState("");
  const [landing, setLanding] = useState("/events");
  const [ticketEnabled, setTicketEnabled] = useState(true);
  const [merchEnabled, setMerchEnabled] = useState(true);
  const [ticketPct, setTicketPct] = useState("5");
  const [merchPct, setMerchPct] = useState("5");
  const [enrollEmail, setEnrollEmail] = useState("");
  const [enrollProgramId, setEnrollProgramId] = useState("");

  async function load() {
    setRows(await fetchAdminReferralPrograms({ scope: "platform" }));
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load programs");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!ticketEnabled && !merchEnabled) {
      setError("Enable at least one of tickets or merchandise");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createAdminReferralProgram({
        name,
        description: description || null,
          public_description:
          "Share one Pàdéyá link. By default earn on ticket and merchandise purchases across events — hosts do not need to opt in. Commission funded by Pàdéyá.",
        enrollment_mode: "manual_enrollment",
        status: "active",
        default_landing_path: landing,
        ticket_rule: ticketEnabled
          ? {
              commission_mode: "percentage",
              commission_value: Number(ticketPct),
            }
          : null,
        merchandise_rule: merchEnabled
          ? {
              commission_mode: "percentage",
              commission_value: Number(merchPct),
            }
          : null,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create program");
    } finally {
      setBusy(false);
    }
  }

  async function onEnroll(e: FormEvent) {
    e.preventDefault();
    if (!enrollProgramId || !enrollEmail.trim()) {
      setError("Program and email are required to enroll");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await enrollAdminReferralProgram(enrollProgramId, {
        email: enrollEmail.trim(),
      });
      setEnrollEmail("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Enrollment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Ambassadors"
      title="Referral programs"
      description="Platform-wide programs use one ambassador link (normally the user’s Fan Passport username). By default they cover tickets and merchandise across events under the program rules — hosts do not opt in. When a host campaign is also enabled and the ambassador is enrolled in both, commissions can stack (host-funded + Pàdéyá-funded). Host event campaigns stay under Campaigns."
    >
      <AdminAmbassadorsNav />
      {error ? <Alert tone="danger" title="Something went wrong">{error}</Alert> : null}

      <Card className="mb-6 space-y-4 p-5">
        <h2 className="text-base font-semibold text-foreground">
          Create platform-wide program
        </h2>
        <p className="text-sm text-muted-foreground">
          Scope: Platform-wide · Default coverage for events and merch under the
          rules you enable — no host tick required. Codes prefer the enrollee’s
          username. Commission funded by Pàdéyá. When the same ambassador is also
          on a live host campaign, host and platform commissions can both apply.
        </p>
        <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Program name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Select
            label="Landing destination"
            value={landing}
            onChange={(e) => setLanding(e.target.value)}
          >
            <option value="/events">Events</option>
            <option value="/">Homepage</option>
            <option value="/shop">Shop</option>
            <option value="/ambassadors">Ambassadors</option>
          </Select>
          <Input
            label="Internal description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="sm:col-span-2"
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={ticketEnabled}
              onChange={(e) => setTicketEnabled(e.target.checked)}
            />
            Ticket commission
          </label>
          {ticketEnabled ? (
            <Input
              label="Ticket commission %"
              type="number"
              min={0}
              max={100}
              step="0.01"
              value={ticketPct}
              onChange={(e) => setTicketPct(e.target.value)}
            />
          ) : (
            <div />
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={merchEnabled}
              onChange={(e) => setMerchEnabled(e.target.checked)}
            />
            Merchandise commission
          </label>
          {merchEnabled ? (
            <Input
              label="Merchandise commission %"
              type="number"
              min={0}
              max={100}
              step="0.01"
              value={merchPct}
              onChange={(e) => setMerchPct(e.target.value)}
            />
          ) : (
            <div />
          )}
          <div className="sm:col-span-2">
            <Button type="submit" disabled={busy}>
              Create platform-wide program
            </Button>
            <Link
              href="/admin/ambassadors/campaigns"
              className="ml-4 text-sm text-muted-foreground underline"
            >
              Or create an event-scoped campaign
            </Link>
          </div>
        </form>
      </Card>

      <Card className="mb-6 space-y-4 p-5">
        <h2 className="text-base font-semibold">Manually enroll ambassador</h2>
        <form onSubmit={onEnroll} className="grid gap-3 sm:grid-cols-3">
          <Select
            label="Program"
            value={enrollProgramId}
            onChange={(e) => setEnrollProgramId(e.target.value)}
          >
            <option value="">Select program</option>
            {(rows || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
          <Input
            label="User email"
            type="email"
            value={enrollEmail}
            onChange={(e) => setEnrollEmail(e.target.value)}
            required
          />
          <div className="flex items-end">
            <Button type="submit" disabled={busy}>
              Enroll
            </Button>
          </div>
        </form>
      </Card>

      {rows === null ? (
        <SkeletonLoader lines={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No platform programs"
          description="Create a platform-wide program to invite ambassadors with one link."
        />
      ) : (
        <div className="space-y-4">
          {rows.map((p) => (
            <Card key={p.id} className="space-y-3 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-semibold">{p.name}</h3>
                <Badge>Platform</Badge>
                <Badge tone="neutral">{p.status}</Badge>
                <Badge tone="success">Funded by Pàdéyá</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                Landing: {p.default_landing_path} · Enrollments:{" "}
                {p.enrollment_count ?? 0} · Window: {p.attribution_window_days}d
              </p>
              <ul className="text-sm text-muted-foreground">
                {p.rules.map((r) => (
                  <li key={r.id}>
                    {r.product_type}: {r.commission_mode} {r.commission_value}
                    {!r.is_active ? " (inactive)" : ""}
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-2">
                {p.status === "active" ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                      void pauseAdminReferralProgram(p.id).then(load).catch((err) =>
                        setError(
                          err instanceof ApiError ? err.detail : "Pause failed",
                        ),
                      )
                    }
                  >
                    Pause
                  </Button>
                ) : p.status === "paused" ? (
                  <Button
                    size="sm"
                    disabled={busy}
                    onClick={() =>
                      void activateAdminReferralProgram(p.id)
                        .then(load)
                        .catch((err) =>
                          setError(
                            err instanceof ApiError
                              ? err.detail
                              : "Activate failed",
                          ),
                        )
                    }
                  >
                    Resume
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}
    </DashboardShell>
  );
}
