"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import {
  Alert,
  Button,
  Input,
  Select,
  Switch,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchHostStorefrontSettings,
  updateHostStorefrontSettings,
  type HostStorefrontSettings,
} from "@/lib/merch-api";

const VISIBILITY_OPTIONS = [
  {
    value: "public",
    label: "Public",
    hint: "Reachable by URL and eligible for public directory links.",
  },
  {
    value: "unlisted",
    label: "Unlisted",
    hint: "Reachable by direct URL only — not linked from public directories.",
  },
  {
    value: "hidden",
    label: "Hidden",
    hint: "Returns 404 for everyone except you (preview).",
  },
] as const;

export function HostStorefrontSettingsCard() {
  const toast = useToast();
  const [settings, setSettings] = useState<HostStorefrontSettings | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] =
    useState<HostStorefrontSettings["visibility"]>("hidden");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchHostStorefrontSettings();
        if (!active) return;
        setSettings(row);
        setEnabled(row.enabled);
        setTitle(row.title ?? "");
        setDescription(row.description ?? "");
        setVisibility(row.visibility);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Could not load storefront settings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const row = await updateHostStorefrontSettings({
        enabled,
        title: title.trim() || null,
        description: description.trim() || null,
        visibility,
      });
      setSettings(row);
      setEnabled(row.enabled);
      setTitle(row.title ?? "");
      setDescription(row.description ?? "");
      setVisibility(row.visibility);
      toast.push({ tone: "success", title: "Storefront settings saved" });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not save storefront settings",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-base font-extrabold tracking-tight text-foreground">
          Merch storefront
        </h2>
        <p className="text-sm text-muted-foreground">
          Control your host merch shop on Pàdéyá. Hidden or disabled shops 404
          for the public.
        </p>
      </div>

      {error ? (
        <Alert tone="danger" title="Storefront settings">
          {error}
        </Alert>
      ) : null}

      {!settings && !error ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : null}

      {settings ? (
        <>
          <Switch
            id="merch-storefront-enabled"
            checked={enabled}
            onCheckedChange={setEnabled}
            label="Enable merch storefront"
            description="When off, the public shop URL returns 404."
          />

          <Input
            label="Storefront title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={160}
            placeholder="Your merch shop title"
          />

          <Textarea
            label="Storefront description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={500}
            rows={3}
            placeholder="Short note about drops, pickup, and exclusives"
          />

          <Select
            label="Visibility"
            value={visibility}
            onChange={(e) =>
              setVisibility(
                e.target.value as HostStorefrontSettings["visibility"],
              )
            }
            hint={
              VISIBILITY_OPTIONS.find((o) => o.value === visibility)?.hint
            }
          >
            {VISIBILITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" size="sm" disabled={busy}>
              {busy ? "Saving…" : "Save storefront"}
            </Button>
            {enabled && visibility !== "hidden" ? (
              <Link
                href={settings.public_path}
                className="text-sm font-semibold text-foreground underline-offset-4 hover:underline"
              >
                Open public shop
              </Link>
            ) : null}
          </div>
        </>
      ) : null}
    </form>
  );
}
