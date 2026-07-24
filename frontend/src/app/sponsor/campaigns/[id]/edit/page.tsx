"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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
  fetchSponsorCampaign,
  updateSponsorCampaign,
} from "@/lib/sponsor-campaigns-api";

export default function EditSponsorCampaignPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const campaignId = params.id;

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
  const [canEdit, setCanEdit] = useState(false);

  useEffect(() => {
    if (!sponsorId || !campaignId) return;
    void (async () => {
      try {
        const row = await fetchSponsorCampaign(sponsorId, campaignId);
        if (!row.can_edit) {
          setCanEdit(false);
          setError("This campaign is read-only for your role or status.");
          return;
        }
        setCanEdit(true);
        setName(row.name);
        setObjective(row.objective);
        setDescription(row.description ?? "");
        setBudgetMin(row.budget_min ?? "");
        setBudgetMax(row.budget_max ?? "");
        setStartDate(row.start_date ?? "");
        setEndDate(row.end_date ?? "");
        setVisibility(row.visibility);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load campaign");
      }
    })();
  }, [campaignId, sponsorId]);

  if (!sponsorId) return null;

  return (
    <Container className="max-w-xl space-y-6 py-6">
      <SectionHeader eyebrow="Campaigns" title="Edit campaign" />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {canEdit ? (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            void (async () => {
              setBusy(true);
              try {
                await updateSponsorCampaign(sponsorId, campaignId, {
                  name,
                  objective,
                  description: description || null,
                  budget_min: budgetMin || null,
                  budget_max: budgetMax || null,
                  start_date: startDate || null,
                  end_date: endDate || null,
                  visibility,
                });
                router.push(`/sponsor/campaigns/${campaignId}`);
              } catch (err) {
                setError(
                  err instanceof ApiError ? err.detail : "Could not save campaign",
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
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Budget min</span>
              <Input
                type="number"
                value={budgetMin}
                onChange={(e) => setBudgetMin(e.target.value)}
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Budget max</span>
              <Input
                type="number"
                value={budgetMax}
                onChange={(e) => setBudgetMax(e.target.value)}
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">Start</span>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="font-semibold">End</span>
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
              <option value="private">Private</option>
              <option value="shared_with_hosts">Shared with hosts</option>
              <option value="public_case_study">Public case study</option>
            </Select>
          </label>
          <div className="flex gap-3">
            <Button type="submit" disabled={busy}>
              Save
            </Button>
            <Link href={`/sponsor/campaigns/${campaignId}`}>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </Link>
          </div>
        </form>
      ) : null}
    </Container>
  );
}
