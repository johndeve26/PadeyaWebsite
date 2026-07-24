"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import {
  ProfileLocationTaxonomyFields,
  type ProfileLocationLabels,
  type ProfileLocationSeed,
} from "@/components/discovery/ProfileLocationTaxonomyFields";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, Input, SectionHeader, Textarea } from "@/components/ui";
import { readRegisterLocationSeed } from "@/lib/auth/register-location";
import { ApiError } from "@/lib/api";
import { fetchFanConnectLocationPreference } from "@/lib/fan-connect-api";
import { onboardHost } from "@/lib/hosts-api";

const steps = [
  "Create your host identity",
  "Publish events & sell tickets",
  "Build Legacy reputation fans trust",
];

export function HostOnboardingForm() {
  const { refreshUser, user } = useAuth();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [location, setLocation] = useState<ProfileLocationLabels>({
    country: "",
    state: "",
    city: "",
  });
  const [locationSeed, setLocationSeed] = useState<ProfileLocationSeed | null>(
    null,
  );
  const [website, setWebsite] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user?.full_name) {
      setDisplayName((prev) => (prev.trim() ? prev : user.full_name));
    }
  }, [user?.full_name]);

  useEffect(() => {
    let alive = true;
    void (async () => {
      const fromRegister = readRegisterLocationSeed();
      const seed: ProfileLocationSeed = {
        country: fromRegister?.country || "Nigeria",
        state: fromRegister?.state,
        city: fromRegister?.city,
      };
      try {
        const pref = await fetchFanConnectLocationPreference();
        if (pref?.country?.trim()) seed.country = pref.country.trim();
        if (pref?.city?.trim()) seed.city = pref.city.trim();
      } catch {
        /* Fan Connect preference is optional */
      }
      if (alive) setLocationSeed(seed);
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onboardHost({
        display_name: displayName,
        bio: bio || undefined,
        city: location.city.trim() || undefined,
        state: location.state.trim() || undefined,
        country: location.country.trim() || undefined,
        website: website || undefined,
      });
      await refreshUser();
      router.push("/host/roadmap");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to complete onboarding");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Host onboarding"
      title="Start hosting on Pàdéyá"
      description="Tell fans who you are. You'll get a Legacy Page, event tools, and a path to verified reputation."
      actions={
        <Link href="/events">
          <Button variant="secondary">Browse as a fan</Button>
        </Link>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <Card variant="dark" className="h-fit space-y-5">
          <SectionHeader
            eyebrow="Why hosts join"
            title="Sell tickets. Prove reputation. Own your audience."
            tone="dark"
          />
          <ol className="space-y-4">
            {steps.map((step, i) => (
              <li key={step} className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-extrabold text-primary-foreground">
                  {i + 1}
                </span>
                <p className="pt-1 text-base text-subtle-foreground">{step}</p>
              </li>
            ))}
          </ol>
        </Card>

        <Card className="space-y-5">
          <SectionHeader
            eyebrow="Profile"
            title="Set up your host identity"
            description="This information appears on your Legacy Page and event listings."
          />
          <form className="space-y-4" onSubmit={onSubmit}>
            <Input
              label="Display name"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your brand or venue name"
            />
            <Textarea
              label="Bio"
              hint="What nights do you put on? Who shows up?"
              rows={4}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />
            {locationSeed ? (
              <ProfileLocationTaxonomyFields
                value={location}
                onChange={setLocation}
                seed={locationSeed}
              />
            ) : null}
            <Input
              label="Website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://…"
            />
            {error ? (
              <Alert tone="danger" title="Unable to complete onboarding">
                {error}
              </Alert>
            ) : null}
            <Button type="submit" size="lg" disabled={submitting} className="w-full sm:w-auto">
              {submitting ? "Creating…" : "Create host profile"}
            </Button>
          </form>
        </Card>
      </div>
    </DashboardShell>
  );
}
