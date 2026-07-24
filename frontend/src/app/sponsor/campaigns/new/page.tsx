"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import {
  Alert,
  Button,
  Container,
  Input,
  SectionHeader,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  CAMPAIGN_OBJECTIVES,
  createSponsorCampaign,
} from "@/lib/sponsor-campaigns-api";

function NewCampaignForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const savedItemId = searchParams.get("saved_item_id");
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;

  const [name, setName] = useState("");
  const [objective, setObjective] = useState("brand_awareness");
  const [description, setDescription] = useState("");
  const [budgetMin, setBudgetMin] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [visibility, setVisibility] = useState("private");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!sponsorId) return null;

  const canCreate =
    active?.is_owner ||
    active?.role === "admin" ||
    active?.role === "campaign_manager";

  if (!canCreate) {
    return (
      <Alert tone="danger" title="Read-only">
        Viewers cannot create campaigns. Ask an owner, admin, or campaign manager.
      </Alert>
    );
  }

  return (
    <Container className="max-w-xl space-y-6 py-6">
      <SectionHeader
        eyebrow="Campaigns"
        title="New campaign"
        description="Campaigns stay private to your sponsor workspace unless you choose visibility that requires Pàdéyá review."
      />
      {savedItemId ? (
        <Alert tone="info" title="Saved item">
          This campaign will include your selected saved item after creation.
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void (async () => {
            setBusy(true);
            try {
              const created = await createSponsorCampaign(sponsorId, {
                name,
                objective,
                description: description || undefined,
                budget_min: budgetMin || undefined,
                budget_max: budgetMax || undefined,
                start_date: startDate || undefined,
                end_date: endDate || undefined,
                visibility,
                sponsor_saved_item_id: savedItemId ?? undefined,
              });
              router.push(`/sponsor/campaigns/${created.id}`);
            } catch (err) {
              setError(
                err instanceof ApiError ? err.detail : "Could not create campaign",
              );
            } finally {
              setBusy(false);
            }
          })();
        }}
      >
        <label className="block space-y-1 text-sm">
          <span className="font-semibold">Name</span>
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="font-semibold">Objective</span>
          <Select value={objective} onChange={(e) => setObjective(e.target.value)}>
            {CAMPAIGN_OBJECTIVES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </label>
        <label className="block space-y-1 text-sm">
          <span className="font-semibold">Description</span>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Internal campaign brief for your team"
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Budget min (NGN)</span>
            <Input
              type="number"
              min={0}
              value={budgetMin}
              onChange={(e) => setBudgetMin(e.target.value)}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Budget max (NGN)</span>
            <Input
              type="number"
              min={0}
              value={budgetMax}
              onChange={(e) => setBudgetMax(e.target.value)}
            />
          </label>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Start date</span>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">End date</span>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </label>
        </div>
        <label className="block space-y-1 text-sm">
          <span className="font-semibold">Visibility</span>
          <Select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
            <option value="private">Private (team only)</option>
            <option value="shared_with_hosts">Shared with hosts (when inquiring)</option>
            <option value="public_case_study">
              Public case study (requires moderation)
            </option>
          </Select>
        </label>
        <div className="flex gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create campaign"}
          </Button>
          <Link href="/sponsor/campaigns">
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </Link>
        </div>
      </form>
    </Container>
  );
}

export default function NewSponsorCampaignPage() {
  return (
    <Suspense>
      <NewCampaignForm />
    </Suspense>
  );
}
