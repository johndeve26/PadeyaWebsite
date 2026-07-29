"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import {
  HostTaxonomyFields,
  emptyHostTaxonomy,
  type HostTaxonomyState,
} from "@/components/hosts/HostTaxonomyFields";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import { GenderFields } from "@/components/profile/GenderFields";
import { ThemeAppearanceCard } from "@/components/theme/ThemeAppearanceCard";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Button,
  Card,
  Input,
  SectionHeader,
  Textarea,
  WorkspaceNavGrid,
  useToast,
  type WorkspaceNavItem,
} from "@/components/ui";
import { updateMyProfile } from "@/lib/admin-lifecycle-api";
import { ApiError } from "@/lib/api";
import {
  DEFAULT_GENDER_VISIBILITY,
  isGender,
  isGenderVisibility,
  type Gender,
  type GenderVisibility,
} from "@/lib/gender";
import { useUnsavedChanges } from "@/lib/hooks/useUnsavedChanges";
import { fetchMyHost, updateMyHost } from "@/lib/hosts-api";
import type { Host } from "@/lib/types/events";

const settingsNav: WorkspaceNavItem[] = [
  {
    href: "/host/team",
    title: "Host Team",
    description: "Invite and archive org-level staff for your host workspace.",
    meta: "Ops",
  },
  {
    href: "/host/bank-accounts",
    title: "Bank accounts",
    description: "Saved payout details — archive instead of hard delete.",
    meta: "Finance",
  },
  {
    href: "/host/legacy/edit",
    title: "Legacy profile",
    description: "Public Legacy Page bio, location, and media.",
    meta: "Reputation",
  },
  {
    href: "/host/merchandise",
    title: "Merch storefront",
    description: "Enable your host merch shop, title, and visibility.",
    meta: "Commerce",
  },
  {
    href: "/host/templates",
    title: "Event templates",
    description: "Reusable draft payloads for faster event creation.",
    meta: "Studio",
  },
];

export default function HostSettingsPage() {
  const toast = useToast();
  const { user, refreshUser } = useAuth();
  const [host, setHost] = useState<Host | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [bio, setBio] = useState("");
  const [website, setWebsite] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [country, setCountry] = useState("");
  const [taxonomy, setTaxonomy] = useState<HostTaxonomyState>(emptyHostTaxonomy());
  const [gender, setGender] = useState<Gender | null>(null);
  const [genderVisibility, setGenderVisibility] = useState<GenderVisibility>(
    DEFAULT_GENDER_VISIBILITY,
  );
  const [savedGender, setSavedGender] = useState<Gender | null>(null);
  const [savedGenderVisibility, setSavedGenderVisibility] =
    useState<GenderVisibility>(DEFAULT_GENDER_VISIBILITY);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [baseline, setBaseline] = useState("");

  const showPersonalGender = Boolean(host?.shows_personal_gender);
  const genderDirty =
    showPersonalGender &&
    (gender !== savedGender || genderVisibility !== savedGenderVisibility);
  const snapshot = JSON.stringify({
    displayName,
    avatarUrl,
    bio,
    website,
    city,
    state,
    country,
    taxonomy,
  });
  const dirty = (Boolean(baseline) && snapshot !== baseline) || genderDirty;
  useUnsavedChanges(dirty);

  useEffect(() => {
    const nextGender = isGender(user?.gender) ? user.gender : null;
    const nextVisibility = isGenderVisibility(user?.gender_visibility)
      ? user.gender_visibility
      : DEFAULT_GENDER_VISIBILITY;
    setGender(nextGender);
    setGenderVisibility(nextVisibility);
    setSavedGender(nextGender);
    setSavedGenderVisibility(nextVisibility);
  }, [user?.gender, user?.gender_visibility]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchMyHost();
        if (!active || !row) return;
        setHost(row);
        const tax: HostTaxonomyState = {
          hostTypeSlugs: row.taxonomy?.host_type_slugs ?? [],
          categorySlugs: row.taxonomy?.category_slugs ?? [],
          audienceSlugs: row.taxonomy?.audience_slugs ?? [],
          primaryCitySlug: row.taxonomy?.primary_city_slug ?? "",
          serviceAreaSlugs: row.taxonomy?.service_area_slugs ?? [],
          nichePositioning: row.taxonomy?.niche_positioning ?? "",
        };
        const next = {
          displayName: row.display_name ?? "",
          avatarUrl: row.profile?.avatar_url ?? "",
          bio: row.profile?.bio ?? "",
          website: row.profile?.website ?? "",
          city: row.profile?.city ?? "",
          state: row.profile?.state ?? "",
          country: row.profile?.country ?? "",
          taxonomy: tax,
        };
        setDisplayName(next.displayName);
        setAvatarUrl(next.avatarUrl);
        setBio(next.bio);
        setWebsite(next.website);
        setCity(next.city);
        setState(next.state);
        setCountry(next.country);
        setTaxonomy(tax);
        setBaseline(JSON.stringify(next));
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load host settings");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (genderDirty && !gender) {
      setError("Select your gender to save.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (genderDirty && gender) {
        await updateMyProfile({
          gender,
          gender_visibility: genderVisibility,
        });
        await refreshUser();
        setSavedGender(gender);
        setSavedGenderVisibility(genderVisibility);
      }
      const updated = await updateMyHost({
        display_name: displayName.trim(),
        avatar_url: avatarUrl.trim() || null,
        bio: bio.trim() || null,
        website: website.trim() || null,
        city: city.trim() || null,
        state: state.trim() || null,
        country: country.trim() || null,
        host_type_slugs: taxonomy.hostTypeSlugs,
        category_slugs: taxonomy.categorySlugs,
        audience_slugs: taxonomy.audienceSlugs,
        primary_city_slug: taxonomy.primaryCitySlug || null,
        service_area_slugs: taxonomy.serviceAreaSlugs,
        niche_positioning: taxonomy.nichePositioning.trim() || null,
      });
      setHost(updated);
      const tax: HostTaxonomyState = {
        hostTypeSlugs: updated.taxonomy?.host_type_slugs ?? [],
        categorySlugs: updated.taxonomy?.category_slugs ?? [],
        audienceSlugs: updated.taxonomy?.audience_slugs ?? [],
        primaryCitySlug: updated.taxonomy?.primary_city_slug ?? "",
        serviceAreaSlugs: updated.taxonomy?.service_area_slugs ?? [],
        nichePositioning: updated.taxonomy?.niche_positioning ?? "",
      };
      const next = {
        displayName: updated.display_name ?? "",
        avatarUrl: updated.profile?.avatar_url ?? "",
        bio: updated.profile?.bio ?? "",
        website: updated.profile?.website ?? "",
        city: updated.profile?.city ?? "",
        state: updated.profile?.state ?? "",
        country: updated.profile?.country ?? "",
        taxonomy: tax,
      };
      setAvatarUrl(next.avatarUrl);
      setTaxonomy(tax);
      setBaseline(JSON.stringify(next));
      toast.push({ tone: "success", title: "Host settings saved" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Manage"
        title="Host Settings"
        description="Manage appearance, host profile, team, and payout bank details."
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}
        {dirty ? (
          <Alert tone="warning" title="Unsaved changes">
            Save before leaving this page.
          </Alert>
        ) : null}

        <WorkspaceNavGrid items={settingsNav} />

        <ThemeAppearanceCard />

        <Card className="space-y-5">
          <SectionHeader
            eyebrow="Profile"
            title={host?.display_name ?? "Host profile"}
            description={`Slug: ${host?.slug ?? "—"} · Status: ${host?.status ?? "—"}`}
          />
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => void onSave(e)}>
            <div className="sm:col-span-2">
              <ImageUrlOrUploadField
                label="Profile photo"
                hint="Same photo as Account settings and Fan Passport."
                value={avatarUrl}
                onChange={setAvatarUrl}
                mediaType="avatar"
                accountAvatar
                previewClassName="h-16 w-16 rounded-full"
              />
            </div>
            <Input
              className="sm:col-span-2"
              label="Display name"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
            {showPersonalGender ? (
              <div className="sm:col-span-2">
                <GenderFields
                  gender={gender}
                  onGenderChange={setGender}
                  genderVisibility={genderVisibility}
                  onVisibilityChange={setGenderVisibility}
                />
              </div>
            ) : null}
            <Textarea
              className="sm:col-span-2"
              label="Bio"
              hint="Shown on your host surfaces where applicable."
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={4}
            />
            <Input
              label="Website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
            />
            <Input
              label="City"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
            <Input
              label="State"
              value={state}
              onChange={(e) => setState(e.target.value)}
            />
            <Input
              label="Country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            />
            <div className="sm:col-span-2 space-y-4 border-t border-border pt-4">
              <SectionHeader
                eyebrow="Discoverability"
                title="Taxonomy & niche"
                description="Host types, categories, and service areas for Legacy and Studio inheritance."
              />
              <HostTaxonomyFields value={taxonomy} onChange={setTaxonomy} />
            </div>
            <div className="sm:col-span-2 flex flex-wrap gap-2">
              <Button type="submit" disabled={busy || !dirty}>
                {busy ? "Saving…" : "Save changes"}
              </Button>
              <Link href="/host/legacy/edit">
                <Button type="button" variant="secondary">
                  Edit Legacy Page
                </Button>
              </Link>
            </div>
          </form>
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
