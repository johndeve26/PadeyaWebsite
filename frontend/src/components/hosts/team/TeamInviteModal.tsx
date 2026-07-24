"use client";

import { useEffect, useState, type FormEvent } from "react";

import { TeamDeskQuickSetup } from "@/components/hosts/team/TeamDeskQuickSetup";
import { TeamEventScopePicker } from "@/components/hosts/team/TeamEventScopePicker";
import { TeamPermissionToggles } from "@/components/hosts/team/TeamPermissionToggles";
import { Button, Input, Modal, Select } from "@/components/ui";
import {
  OWNER_ONLY_PERMISSION_KEYS,
  TEAM_ROLE_OPTIONS,
  defaultScopeForRole,
  mergePermissions,
  permissionsForRole,
  type TeamScope,
} from "@/lib/host-team-roles";
import {
  inviteHostTeamMember,
  lookupHostTeamInvitee,
  type HostTeamInviteLookup,
} from "@/lib/hosts-lifecycle-api";
import { ApiError } from "@/lib/api";
import type { EventItem } from "@/lib/types/events";
import type {
  HostTeamPermissionKey,
  HostTeamPermissions,
} from "@/lib/types/lifecycle";

type Props = {
  open: boolean;
  onClose: () => void;
  hostId: string | null;
  isOwner: boolean;
  events: EventItem[];
  initialRole?: string;
  onInvited: () => Promise<void> | void;
  onError: (detail: string) => void;
  onSuccess: (message: string) => void;
};

type FormBodyProps = {
  hostId: string | null;
  isOwner: boolean;
  events: EventItem[];
  initialRole: string;
  busy: boolean;
  setBusy: (busy: boolean) => void;
  onClose: () => void;
  onInvited: () => Promise<void> | void;
  onError: (detail: string) => void;
  onSuccess: (message: string) => void;
  onCanSubmitChange: (ok: boolean) => void;
};

function looksLikeEmail(raw: string): boolean {
  const value = raw.trim().toLowerCase();
  if (value.startsWith("@") || value.includes(" ")) return false;
  if ((value.match(/@/g) || []).length !== 1) return false;
  const [, domain = ""] = value.split("@");
  return domain.includes(".");
}

function looksLikeUsernameCandidate(raw: string): boolean {
  const value = raw.trim();
  if (!value) return false;
  if (looksLikeEmail(value)) return false;
  if (value.startsWith("@")) return value.length >= 2;
  return /^[a-zA-Z0-9_]{3,32}$/.test(value);
}

function InviteePreview({
  invitee,
  lookup,
  lookingUp,
}: {
  invitee: string;
  lookup: HostTeamInviteLookup | null;
  lookingUp: boolean;
}) {
  const trimmed = invitee.trim();
  if (!trimmed) return null;

  if (looksLikeEmail(trimmed)) {
    return (
      <div className="rounded-md border border-border bg-muted/40 px-3 py-2.5 text-sm text-foreground">
        <p className="font-medium">{trimmed}</p>
        <p className="mt-0.5 text-muted-foreground">
          Invite will be sent to this email.
        </p>
      </div>
    );
  }

  if (!looksLikeUsernameCandidate(trimmed)) return null;

  if (lookingUp) {
    return (
      <div className="rounded-md border border-border bg-muted/40 px-3 py-2.5 text-sm text-muted-foreground">
        Looking up Pàdéyá username…
      </div>
    );
  }

  if (lookup?.invite_method === "username" && lookup.found) {
    return (
      <div className="flex items-start gap-3 rounded-md border border-border bg-muted/40 px-3 py-2.5">
        {lookup.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={lookup.avatar_url}
            alt=""
            className="h-10 w-10 shrink-0 rounded-full object-cover"
          />
        ) : (
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold text-muted-foreground"
            aria-hidden
          >
            {(lookup.display_name || lookup.username || "?").slice(0, 1).toUpperCase()}
          </div>
        )}
        <div className="min-w-0 space-y-0.5 text-sm">
          <p className="font-semibold text-foreground">
            {lookup.display_name || lookup.username}
          </p>
          <p className="text-muted-foreground">{lookup.username}</p>
          <p className="text-muted-foreground">This user will receive an invite.</p>
        </div>
      </div>
    );
  }

  if (lookup?.invite_method === "username" && lookup.valid && !lookup.found) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm text-destructive">
        No Pàdéyá user found with that username.
      </div>
    );
  }

  return null;
}

function TeamInviteFormBody({
  hostId,
  isOwner,
  events,
  initialRole,
  busy,
  setBusy,
  onClose,
  onInvited,
  onError,
  onSuccess,
  onCanSubmitChange,
}: FormBodyProps) {
  const [invitee, setInvitee] = useState("");
  const [role, setRole] = useState(initialRole);
  const [scope, setScope] = useState<TeamScope>(() =>
    defaultScopeForRole(initialRole),
  );
  const [eventIds, setEventIds] = useState<string[]>([]);
  const [perms, setPerms] = useState<HostTeamPermissions>(() =>
    permissionsForRole(initialRole),
  );
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [lookup, setLookup] = useState<HostTeamInviteLookup | null>(null);
  const [lookingUp, setLookingUp] = useState(false);

  useEffect(() => {
    const trimmed = invitee.trim();
    if (!trimmed) {
      queueMicrotask(() => {
        setLookup(null);
        setLookingUp(false);
        onCanSubmitChange(false);
      });
      return;
    }

    if (looksLikeEmail(trimmed)) {
      queueMicrotask(() => {
        setLookup(null);
        setLookingUp(false);
        onCanSubmitChange(true);
      });
      return;
    }

    if (!looksLikeUsernameCandidate(trimmed)) {
      queueMicrotask(() => {
        setLookup(null);
        setLookingUp(false);
        onCanSubmitChange(false);
      });
      return;
    }

    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setLookingUp(true);
      onCanSubmitChange(false);
    });
    const timer = window.setTimeout(async () => {
      try {
        const result = await lookupHostTeamInvitee(trimmed, hostId);
        if (cancelled) return;
        setLookup(result);
        onCanSubmitChange(Boolean(result.valid && result.found));
      } catch {
        if (cancelled) return;
        setLookup({
          invite_method: "username",
          valid: true,
          found: false,
          display_name: null,
          username: trimmed.startsWith("@") ? trimmed : `@${trimmed}`,
          avatar_url: null,
          masked_email: null,
          message: "No Pàdéyá user found with that username.",
        });
        onCanSubmitChange(false);
      } finally {
        if (!cancelled) setLookingUp(false);
      }
    }, 320);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [invitee, hostId, onCanSubmitChange]);

  function applyRole(next: string) {
    setRole(next);
    setScope(defaultScopeForRole(next));
    setPerms(permissionsForRole(next));
  }

  function togglePerm(key: HostTeamPermissionKey) {
    if (!isOwner && OWNER_ONLY_PERMISSION_KEYS.includes(key)) return;
    setPerms((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = invitee.trim();
    if (!trimmed) return;
    if (looksLikeUsernameCandidate(trimmed) && !(lookup?.found)) {
      onError("No Pàdéyá user found with that username.");
      return;
    }
    setBusy(true);
    try {
      const label =
        TEAM_ROLE_OPTIONS.find((o) => o.value === role)?.label.split(" — ")[0] ||
        role;
      await inviteHostTeamMember(
        {
          invite_identifier: trimmed,
          role,
          role_label: label,
          permissions_json: mergePermissions(perms),
          scope_json: {
            type: scope,
            event_ids: scope === "selected_events" ? eventIds : [],
          },
          selected_event_ids:
            scope === "selected_events" ? eventIds : undefined,
        },
        hostId,
      );
      onSuccess(
        "They’ll get an invite email to join your Pàdéyá host team. Link expires in 7 days.",
      );
      await onInvited();
      onClose();
    } catch (err) {
      onError(err instanceof ApiError ? err.detail : "Invite failed");
    } finally {
      setBusy(false);
    }
  }

  const deskFocused = role === "scanner" || role === "merch_staff";

  return (
    <form id="team-invite-form" className="space-y-4" onSubmit={onSubmit}>
      <div className="space-y-2">
        <Input
          label="Email or Pàdéyá username"
          type="text"
          autoComplete="off"
          inputMode="text"
          spellCheck={false}
          value={invitee}
          onChange={(e) => setInvitee(e.target.value)}
          onBlur={() => setInvitee((v) => v.trim())}
          placeholder="name@example.com or @username"
          hint="One field — email invite, or Pàdéyá username (with or without @)."
          required
        />
        <InviteePreview
          invitee={invitee}
          lookup={lookup}
          lookingUp={lookingUp}
        />
      </div>

      <TeamDeskQuickSetup
        role={role}
        scope={scope}
        perms={perms}
        disabled={busy}
        onApply={({ role: nextRole, scope: nextScope, perms: nextPerms }) => {
          setRole(nextRole);
          setScope(nextScope);
          setPerms(nextPerms);
        }}
      />

      <Select
        label="Role preset"
        value={role}
        onChange={(e) => applyRole(e.target.value)}
        disabled={busy}
      >
        {TEAM_ROLE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </Select>

      <TeamEventScopePicker
        scope={scope}
        onScopeChange={setScope}
        eventIds={eventIds}
        onEventIdsChange={setEventIds}
        events={events}
        disabled={busy}
        hint={
          deskFocused
            ? "For scanner/merch, pick the events they’ll work — desk access stays event-scoped unless you choose host-wide."
            : undefined
        }
      />

      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-semibold text-foreground">Permissions</p>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setShowAdvanced((v) => !v)}
          >
            {showAdvanced ? "Hide toggles" : "Edit permission toggles"}
          </Button>
        </div>
        {!showAdvanced ? (
          <p className="text-xs text-muted-foreground">
            Using the {role.replace(/_/g, " ")} preset
            {deskFocused
              ? " — ticket/merch desk keys stay off host-wide unless you used “all events”."
              : "."}{" "}
            Open toggles to customize before sending.
          </p>
        ) : (
          <TeamPermissionToggles
            perms={perms}
            onToggle={togglePerm}
            isOwner={isOwner}
            disabled={busy}
            compact
            groupTitles={
              deskFocused ? ["Events", "Tickets", "Merch"] : undefined
            }
          />
        )}
      </div>
    </form>
  );
}

export function TeamInviteModal({
  open,
  onClose,
  hostId,
  isOwner,
  events,
  initialRole = "scanner",
  onInvited,
  onError,
  onSuccess,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [canSubmit, setCanSubmit] = useState(false);

  function handleClose() {
    setBusy(false);
    setCanSubmit(false);
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Invite team member"
      description="Email or Pàdéyá username, role preset, permissions, and event scope."
      className="sm:max-w-xl"
      footer={
        <>
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={busy}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            form="team-invite-form"
            disabled={busy || !open || !canSubmit}
          >
            {busy ? "Sending…" : "Send invite"}
          </Button>
        </>
      }
    >
      {open ? (
        <TeamInviteFormBody
          key={initialRole}
          hostId={hostId}
          isOwner={isOwner}
          events={events}
          initialRole={initialRole}
          busy={busy}
          setBusy={setBusy}
          onClose={handleClose}
          onInvited={onInvited}
          onError={onError}
          onSuccess={onSuccess}
          onCanSubmitChange={setCanSubmit}
        />
      ) : null}
    </Modal>
  );
}
