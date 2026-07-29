"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Alert,
  Button,
  Card,
  Checkbox,
  EmptyState,
  SkeletonLoader,
  Switch,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchFanConnectSettings,
  updateFanConnectSettings,
} from "@/lib/fan-connect-api";
import {
  trackFanConnectPageView,
  trackFanConnectSettingsUpdated,
} from "@/lib/analytics";
import {
  fetchMessageSettings,
  unblockMessagingUser,
} from "@/lib/messaging-api";
import { formatDate } from "@/lib/format";
import type {
  FanConnectRequestPolicy,
  FanConnectSettings,
} from "@/lib/types/fan-connect";
import type { BlockedUser } from "@/lib/types/messaging";

type VisibilityKey =
  | "fan_connect_enabled"
  | "discoverable_for_same_events"
  | "discoverable_for_similar_interests"
  | "allow_connection_requests";

type VisibilityToggle = {
  key: VisibilityKey;
  label: string;
  hint: string;
};

type SeeKey =
  | "show_shared_hosts"
  | "show_shared_categories"
  | "show_shared_public_events"
  | "show_public_city";

type SeeToggle = {
  key: SeeKey;
  label: string;
  hint: string;
};

const VISIBILITY: VisibilityToggle[] = [
  {
    key: "fan_connect_enabled",
    label: "Enable Fan Connect",
    hint: "On by default. Meet Explorers going where you’re going — turn off anytime.",
  },
  {
    key: "discoverable_for_same_events",
    label: "Let Explorers going to the same event find me",
    hint: "Appear in suggestions for members who share public nights with you.",
  },
  {
    key: "discoverable_for_similar_interests",
    label: "Let members with similar event interests find me",
    hint: "Appear when favorite scenes overlap — turn off anytime.",
  },
  {
    key: "allow_connection_requests",
    label: "Allow connection requests",
    hint: "Other members may send a Connect request when eligible.",
  },
];

const WHAT_OTHERS_SEE: SeeToggle[] = [
  {
    key: "show_shared_hosts",
    label: "Show shared hosts",
    hint: "Display hosts you both follow as safe context.",
  },
  {
    key: "show_shared_categories",
    label: "Show shared categories",
    hint: "Display overlapping favorite scenes.",
  },
  {
    key: "show_shared_public_events",
    label: "Show shared public events",
    hint: "Display shared public check-ins — never private nights.",
  },
  {
    key: "show_public_city",
    label: "Show public city/category stats",
    hint: "Only when both of you enable this — never private venues.",
  },
];

const POLICY_OPTIONS: {
  value: FanConnectRequestPolicy;
  label: string;
  hint: string;
}[] = [
  {
    value: "same_event",
    label: "Explorers going to same public event",
    hint: "Requests only with a shared listed public night.",
  },
  {
    value: "same_host",
    label: "Members who follow same hosts",
    hint: "Shared host follow or public event is enough.",
  },
  {
    value: "public_passports",
    label: "Members with public Passports",
    hint: "Any safe shared public reason (events, hosts, or scenes).",
  },
  {
    value: "nobody",
    label: "Nobody",
    hint: "Pause all new connection requests.",
  },
];

function normalizePolicies(
  settings: FanConnectSettings,
): FanConnectRequestPolicy[] {
  const raw = settings.request_policies?.length
    ? settings.request_policies
    : [settings.request_policy];
  const cleaned = raw.filter((p): p is FanConnectRequestPolicy =>
    POLICY_OPTIONS.some((opt) => opt.value === p),
  );
  if (cleaned.includes("nobody")) return ["nobody"];
  if (cleaned.length === 0) {
    return POLICY_OPTIONS.map((o) => o.value).filter((v) => v !== "nobody");
  }
  return POLICY_OPTIONS.map((o) => o.value).filter(
    (v) => v !== "nobody" && cleaned.includes(v),
  );
}

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-extrabold text-heading">{title}</h2>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
      <Card className="divide-y divide-border p-0">{children}</Card>
    </section>
  );
}

function ToggleRow({
  label,
  hint,
  checked,
  disabled,
  onCheckedChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  disabled?: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 py-4">
      <div>
        <p className="text-sm font-semibold text-heading">{label}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{hint}</p>
      </div>
      <Switch
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
      />
    </div>
  );
}

export function ConnectSettingsForm() {
  const toast = useToast();
  const [settings, setSettings] = useState<FanConnectSettings | null>(null);
  const [blocked, setBlocked] = useState<BlockedUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function loadBlocked() {
    try {
      const msg = await fetchMessageSettings();
      setBlocked(msg.blocked_users || []);
    } catch {
      setBlocked([]);
    }
  }

  useEffect(() => {
    trackFanConnectPageView({ path: "/connect/settings" });
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchFanConnectSettings();
        if (!active) return;
        setSettings({
          ...data,
          request_policies: normalizePolicies(data),
        });
        await loadBlocked();
      } catch (err) {
        if (active)
          setError(
            err instanceof ApiError
              ? err.detail
              : "Could not load Fan Connect settings.",
          );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function save(patch: Partial<FanConnectSettings>) {
    if (!settings) return;
    setSaving(true);
    setError(null);
    try {
      const next = await updateFanConnectSettings(patch);
      setSettings({
        ...next,
        request_policies: normalizePolicies(next),
      });
      trackFanConnectSettingsUpdated({
        fanConnectEnabled: next.fan_connect_enabled,
        requestPolicy: next.request_policy,
      });
      toast.push({ tone: "success", title: "Settings saved" });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not save settings.",
      );
    } finally {
      setSaving(false);
    }
  }

  function togglePolicy(value: FanConnectRequestPolicy, checked: boolean) {
    if (!settings) return;
    const current = normalizePolicies(settings);
    let next: FanConnectRequestPolicy[];

    if (value === "nobody") {
      next = checked ? ["nobody"] : ["same_event"];
    } else if (checked) {
      const withoutNobody = current.filter((p) => p !== "nobody" && p !== value);
      next = POLICY_OPTIONS.map((o) => o.value).filter(
        (v) => v !== "nobody" && (withoutNobody.includes(v) || v === value),
      );
    } else {
      next = current.filter((p) => p !== value && p !== "nobody");
      if (next.length === 0) next = ["nobody"];
    }

    setSettings({ ...settings, request_policies: next });
    void save({ request_policies: next });
  }

  async function disableConnect() {
    setSaving(true);
    setError(null);
    try {
      const next = await updateFanConnectSettings({
        fan_connect_enabled: false,
        allow_connection_requests: false,
        discoverable_for_same_events: false,
        discoverable_for_similar_interests: false,
      });
      setSettings({
        ...next,
        request_policies: normalizePolicies(next),
      });
      trackFanConnectSettingsUpdated({
        fanConnectEnabled: false,
        requestPolicy: next.request_policy,
      });
      toast.push({ tone: "success", title: "Fan Connect disabled" });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not disable Fan Connect.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <SkeletonLoader className="h-48" />;
  if (!settings) {
    return (
      <Alert tone="danger">
        {error || "Fan Connect settings unavailable."}
      </Alert>
    );
  }

  const selectedPolicies = normalizePolicies(settings);

  return (
    <div className="space-y-8">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <Card className="space-y-2 border-primary/20 bg-primary/5 p-5">
        <p className="text-sm font-extrabold text-heading">
          On by default — untick anytime
        </p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Fan Connect and discovery start enabled so you can meet Explorers
          going where you’re going. Turn any toggle off when you want privacy.
          Directory listing is separate. Chat unlocks only after both of you
          accept — no phone numbers or private venues.
        </p>
      </Card>

      <SettingsSection
        title="Visibility"
        description="Control whether you appear in Fan Connect and who can request."
      >
        {VISIBILITY.map((t) => (
          <ToggleRow
            key={t.key}
            label={t.label}
            hint={t.hint}
            checked={Boolean(settings[t.key])}
            disabled={saving}
            onCheckedChange={(checked) => {
              setSettings({ ...settings, [t.key]: checked });
              void save({ [t.key]: checked });
            }}
          />
        ))}
      </SettingsSection>

      <SettingsSection
        title="What others can see"
        description="Safe public context only — never tickets, spend, or hidden venues."
      >
        {WHAT_OTHERS_SEE.map((t) => (
          <ToggleRow
            key={t.key}
            label={t.label}
            hint={t.hint}
            checked={Boolean(settings[t.key])}
            disabled={saving}
            onCheckedChange={(checked) => {
              setSettings({ ...settings, [t.key]: checked });
              void save({ [t.key]: checked });
            }}
          />
        ))}
        <div className="flex items-start justify-between gap-4 px-5 py-4">
          <div>
            <p className="text-sm font-semibold text-heading">
              Hide private events always
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              Enforced on Pàdéyá — private and secret nights never appear in
              Connect context or reasons.
            </p>
          </div>
          <Switch
            checked
            disabled
            onCheckedChange={() => undefined}
            aria-label="Hide private events always"
          />
        </div>
      </SettingsSection>

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-extrabold text-heading">
            Who can send requests
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            Choose one or more ways people can become eligible to request.
          </p>
        </div>
        <Card className="space-y-4 p-5">
          {POLICY_OPTIONS.map((opt) => (
            <Checkbox
              key={opt.value}
              id={`request_policy_${opt.value}`}
              name="request_policies"
              value={opt.value}
              label={opt.label}
              hint={opt.hint}
              checked={selectedPolicies.includes(opt.value)}
              disabled={saving}
              onChange={(e) => {
                togglePolicy(opt.value, e.target.checked);
              }}
            />
          ))}
        </Card>
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-extrabold text-heading">Safety</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            Blocks apply across messaging and Fan Connect. Reports stay with
            Pàdéyá moderation.
          </p>
        </div>

        <Card className="space-y-4 p-5">
          <div>
            <h3 className="text-sm font-extrabold text-heading">Blocked fans</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Blocked accounts cannot message you or appear in Connect
              suggestions. Display names only.
            </p>
          </div>
          {blocked.length === 0 ? (
            <EmptyState
              title="No blocked fans"
              description="When you block someone from Connect or messages, they appear here."
              className="py-8"
            />
          ) : (
            <ul className="space-y-3">
              {blocked.map((b) => (
                <li
                  key={b.user_id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-border px-3 py-3"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-heading">{b.display_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {b.username ? `@${b.username}` : b.role}
                      {b.reason ? ` · ${b.reason}` : ""}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      {formatDate(b.created_at)}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={saving}
                    onClick={() => {
                      setSaving(true);
                      void unblockMessagingUser(b.user_id, false)
                        .then(() => loadBlocked())
                        .then(() =>
                          toast.push({
                            tone: "success",
                            title: "Unblocked",
                          }),
                        )
                        .catch((err) =>
                          setError(
                            err instanceof ApiError
                              ? err.detail
                              : "Could not unblock.",
                          ),
                        )
                        .finally(() => setSaving(false));
                    }}
                  >
                    Unblock
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-muted-foreground">
            Manage message preferences anytime in{" "}
            <Link
              href="/dashboard/messages/settings"
              className="font-semibold text-primary hover:underline"
            >
              message settings
            </Link>
            .
          </p>
        </Card>

        <Card className="space-y-3 p-5">
          <div>
            <h3 className="text-sm font-extrabold text-heading">Report history</h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              Reports you submit from Connect or messages are reviewed by
              Pàdéyá moderation. Details stay private — we don’t show a public
              report trail on your Passport.
            </p>
          </div>
        </Card>

        <Card className="space-y-3 border-danger/20 p-5">
          <div>
            <h3 className="text-sm font-extrabold text-heading">
              Disable Fan Connect
            </h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              Turns Connect off and stops discovery and new requests. Existing
              chats stay gated by connection status.
            </p>
          </div>
          <Button
            variant="secondary"
            disabled={saving || !settings.fan_connect_enabled}
            onClick={() => void disableConnect()}
          >
            Disable Fan Connect
          </Button>
        </Card>
      </section>
    </div>
  );
}
