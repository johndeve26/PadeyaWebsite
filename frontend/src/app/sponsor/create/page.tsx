"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
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
import { createSponsorProfile } from "@/lib/sponsor-profiles-api";

const TYPES = [
  { value: "brand", label: "Brand" },
  { value: "business", label: "Business" },
  { value: "agency", label: "Agency" },
  { value: "creator", label: "Creator" },
  { value: "media_partner", label: "Media partner" },
  { value: "community", label: "Community" },
  { value: "ngo", label: "NGO" },
  { value: "government", label: "Government" },
  { value: "other", label: "Other" },
];

export default function SponsorCreatePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [sponsorType, setSponsorType] = useState("brand");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [shortBio, setShortBio] = useState("");
  const [locations, setLocations] = useState("");
  const [goals, setGoals] = useState("");
  const [budget, setBudget] = useState("");
  const [submitReview, setSubmitReview] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createSponsorProfile({
        display_name: displayName.trim(),
        sponsor_type: sponsorType,
        industry: industry.trim() || undefined,
        website_url: website.trim() || undefined,
        short_bio: shortBio.trim() || undefined,
        target_locations: locations
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        campaign_goals: goals
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        budget_range: budget.trim() || undefined,
        contact_email: user?.email,
        submit_for_review: submitReview,
      });
      router.push("/sponsor");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create sponsor");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <Container className="max-w-xl space-y-6 py-10">
        <SectionHeader
          eyebrow="Sponsor onboarding"
          title="Create sponsor profile"
          description="Set up a sponsor identity separate from Host. Profiles stay private until admin verification for public visibility."
        />
        {error ? (
          <Alert tone="danger" title="Could not save">
            {error}
          </Alert>
        ) : null}
        <form className="space-y-4" onSubmit={(e) => void onSubmit(e)}>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Sponsor name</span>
            <Input
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Sponsor type</span>
            <Select
              value={sponsorType}
              onChange={(e) => setSponsorType(e.target.value)}
            >
              {TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Industry</span>
            <Input value={industry} onChange={(e) => setIndustry(e.target.value)} />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Website</span>
            <Input value={website} onChange={(e) => setWebsite(e.target.value)} />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Short bio</span>
            <Textarea value={shortBio} onChange={(e) => setShortBio(e.target.value)} />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Target locations (comma-separated)</span>
            <Input value={locations} onChange={(e) => setLocations(e.target.value)} />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Campaign goals (comma-separated)</span>
            <Input value={goals} onChange={(e) => setGoals(e.target.value)} />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-semibold">Budget range (optional)</span>
            <Input value={budget} onChange={(e) => setBudget(e.target.value)} />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={submitReview}
              onChange={(e) => setSubmitReview(e.target.checked)}
            />
            Submit for admin review (recommended before public listing)
          </label>
          <div className="flex gap-3">
            <Button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Create sponsor"}
            </Button>
            <Link href="/dashboard">
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </Link>
          </div>
        </form>
      </Container>
    </main>
  );
}
