"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { LegacyContactSettingsEditor } from "@/components/legacy/studio/LegacyContactSettingsEditor";
import { LegacyCtaSettingsEditor } from "@/components/legacy/studio/LegacyCtaSettingsEditor";
import {
  LegacySocialLinksEditor,
  socialLinksToDraft,
} from "@/components/legacy/studio/LegacySocialLinksEditor";
import { LegacyStudioShell } from "@/components/legacy/studio/LegacyStudioShell";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import { Alert, Button, Card, Input, SectionHeader, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { errorDetail } from "@/lib/api-timeouts";
import { fetchMyLegacyPage, updateMyLegacyProfile } from "@/lib/legacy-api";
import type { LegacyContactSettings } from "@/lib/types/legacy";

export default function HostLegacyEditPage() {
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [tagline, setTagline] = useState("");
  const [bio, setBio] = useState("");
  const [website, setWebsite] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [country, setCountry] = useState("");
  const [serviceAreas, setServiceAreas] = useState("");
  const [hostType, setHostType] = useState("");
  const [primaryCategory, setPrimaryCategory] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [sponsorshipAvailable, setSponsorshipAvailable] = useState(false);
  const [sponsorshipNote, setSponsorshipNote] = useState("");
  const [primaryCtaLabel, setPrimaryCtaLabel] = useState("");
  const [primaryCtaType, setPrimaryCtaType] = useState("vault");
  const [primaryCtaValue, setPrimaryCtaValue] = useState("");
  const [secondaryCtaLabel, setSecondaryCtaLabel] = useState("");
  const [secondaryCtaType, setSecondaryCtaType] = useState("events");
  const [secondaryCtaValue, setSecondaryCtaValue] = useState("#upcoming-events");
  const [socialLinks, setSocialLinks] = useState<
    { platform: string; url: string; label: string }[]
  >([]);
  const [contact, setContact] = useState<LegacyContactSettings>({
    preference: "none",
    public_email: null,
    show_contact_form: false,
    preferred_channel: null,
    note: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const page = await fetchMyLegacyPage();
        if (!active) return;
        setDisplayName(page.display_name);
        setUsername(page.username);
        setTagline(page.tagline || page.settings?.tagline || "");
        setBio(page.about ?? "");
        setWebsite(page.profile?.website ?? "");
        setCity(page.profile?.city ?? "");
        setState(page.profile?.state ?? "");
        setCountry(page.profile?.country ?? "");
        setServiceAreas(
          Array.isArray(page.settings?.service_areas)
            ? page.settings!.service_areas!.map(String).join(", ")
            : "",
        );
        setHostType(page.settings?.host_type_slug || "");
        setPrimaryCategory(page.settings?.primary_category_slug || "");
        setAvatarUrl(page.profile?.avatar_url ?? "");
        setCoverUrl(page.profile?.cover_url ?? "");
        setSponsorshipAvailable(Boolean(page.settings?.sponsorship_available));
        setSponsorshipNote(page.settings?.sponsorship_note || "");
        setPrimaryCtaLabel(page.settings?.primary_cta_label || "");
        setPrimaryCtaType(page.settings?.primary_cta_type || "vault");
        setPrimaryCtaValue(page.settings?.primary_cta_value || "");
        setSecondaryCtaLabel(page.settings?.secondary_cta_label || "");
        setSecondaryCtaType(page.settings?.secondary_cta_type || "events");
        setSecondaryCtaValue(page.settings?.secondary_cta_value || "#upcoming-events");
        setSocialLinks(socialLinksToDraft(page.social_links));
        if (page.contact) setContact(page.contact);
      } catch (err) {
        if (active) {
          setError(errorDetail(err, "Failed to load profile"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateMyLegacyProfile({
        display_name: displayName,
        username: username || undefined,
        tagline: tagline || null,
        bio: bio || null,
        website: website || null,
        city: city || null,
        state: state || null,
        country: country || null,
        avatar_url: avatarUrl || null,
        cover_url: coverUrl || null,
        host_type_slug: hostType || null,
        primary_category_slug: primaryCategory || null,
        service_areas: serviceAreas
          ? serviceAreas.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        sponsorship_available: sponsorshipAvailable,
        sponsorship_note: sponsorshipNote || null,
        primary_cta_label: primaryCtaLabel || null,
        primary_cta_type: primaryCtaType || null,
        primary_cta_value: primaryCtaValue || null,
        secondary_cta_label: secondaryCtaLabel || null,
        secondary_cta_type: secondaryCtaType || null,
        secondary_cta_value: secondaryCtaValue || null,
        social_links: socialLinks.filter((l) => l.platform && l.url),
        contact: {
          preference: contact.preference,
          public_email: contact.public_email ?? null,
          show_contact_form: contact.show_contact_form,
          preferred_channel: contact.preferred_channel ?? null,
          note: contact.note ?? null,
        },
      });
      setUsername(updated.username);
      setSaved(true);
    } catch (err) {
      setError(errorDetail(err, "Save failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <LegacyStudioShell
      title="Edit Legacy profile"
      description="Identity, CTAs, socials, and contact settings for your public Legacy hub."
      actions={
        username ? (
          <Link href={`/@${username}`}>
            <Button size="sm" variant="secondary">
              View public page
            </Button>
          </Link>
        ) : null
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {saved ? (
        <Alert tone="success" title="Legacy saved">
          Your public Legacy Page settings are updated.
        </Alert>
      ) : null}

      <Card className="max-w-3xl space-y-6">
        <Alert tone="info" title="Public URL">
          /@{username || "…"}
        </Alert>

        <form className="space-y-8" onSubmit={onSubmit}>
          <section className="space-y-4">
            <SectionHeader title="Identity" description="How fans see you on Pàdéyá." />
            <Input
              label="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
            <Input
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              hint="Becomes /@{username}. Changing this updates your public Legacy URL."
              required
            />
            <Input
              label="Short tagline"
              value={tagline}
              onChange={(e) => setTagline(e.target.value)}
              placeholder="Nights that travel."
              hint="One line under your name on the public page."
            />
            <Textarea
              label="Bio"
              rows={5}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Tell fans about your nights, cities, and what to expect…"
              hint="Tell fans about your events, vibe, and reputation."
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Host type"
                value={hostType}
                onChange={(e) => setHostType(e.target.value)}
                placeholder="dj, promoter, collective…"
                hint="How you describe your role (slug-style, e.g. dj)."
              />
              <Input
                label="Primary category"
                value={primaryCategory}
                onChange={(e) => setPrimaryCategory(e.target.value)}
                placeholder="nightlife, culture, live-music…"
                hint="Main scene fans associate with you."
              />
            </div>
            <Input
              label="Website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://yourbrand.com"
              hint="Optional personal or brand site (separate from hero buttons)."
            />
          </section>

          <section className="space-y-4">
            <SectionHeader title="Location & service areas" />
            <div className="grid gap-4 sm:grid-cols-3">
              <Input label="City" value={city} onChange={(e) => setCity(e.target.value)} />
              <Input label="State" value={state} onChange={(e) => setState(e.target.value)} />
              <Input
                label="Country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              />
            </div>
            <Input
              label="Service areas"
              value={serviceAreas}
              onChange={(e) => setServiceAreas(e.target.value)}
              placeholder="Lagos Island, VI, Lekki"
              hint="Comma-separated."
            />
          </section>

          <section className="space-y-4">
            <SectionHeader
              title="Media"
              description="Upload profile and cover images, or paste URLs."
            />
            <ImageUrlOrUploadField
              label="Profile image"
              hint="Same photo as Account settings and Fan Passport."
              value={avatarUrl}
              onChange={setAvatarUrl}
              mediaType="avatar"
              accountAvatar
              previewClassName="h-16 w-16 rounded-full"
            />
            <ImageUrlOrUploadField
              label="Cover image"
              value={coverUrl}
              onChange={setCoverUrl}
              mediaType="other"
              previewClassName="h-14 w-28"
            />
          </section>

          <section className="space-y-4">
            <SectionHeader
              title="Hero buttons & sponsorship"
              description="Buttons fans see first on your public Legacy Page, plus whether brands can inquire."
            />
            <LegacyCtaSettingsEditor
              value={{
                primaryLabel: primaryCtaLabel,
                primaryType: primaryCtaType,
                primaryValue: primaryCtaValue,
                secondaryLabel: secondaryCtaLabel,
                secondaryType: secondaryCtaType,
                secondaryValue: secondaryCtaValue,
                sponsorshipAvailable,
                sponsorshipNote,
              }}
              onChange={(next) => {
                setPrimaryCtaLabel(next.primaryLabel);
                setPrimaryCtaType(next.primaryType);
                setPrimaryCtaValue(next.primaryValue);
                setSecondaryCtaLabel(next.secondaryLabel);
                setSecondaryCtaType(next.secondaryType);
                setSecondaryCtaValue(next.secondaryValue);
                setSponsorshipAvailable(next.sponsorshipAvailable);
                setSponsorshipNote(next.sponsorshipNote);
              }}
            />
          </section>

          <LegacySocialLinksEditor value={socialLinks} onChange={setSocialLinks} />
          <LegacyContactSettingsEditor value={contact} onChange={setContact} />

          <Button type="submit" disabled={busy} size="lg">
            {busy ? "Saving…" : "Save Legacy profile"}
          </Button>
        </form>
      </Card>
    </LegacyStudioShell>
  );
}
