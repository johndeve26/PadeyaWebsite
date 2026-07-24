"use client";

import { useState, type FormEvent } from "react";

import { Button, Input, Modal, Select } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { inviteSponsorTeamMember } from "@/lib/sponsor-team-api";

const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "campaign_manager", label: "Campaign manager" },
  { value: "viewer", label: "Viewer" },
];

type Props = {
  open: boolean;
  sponsorId: string;
  onClose: () => void;
  onInvited: () => Promise<void> | void;
  onError: (detail: string) => void;
  onSuccess: (message: string) => void;
};

function isValidEmail(value: string): boolean {
  const v = value.trim();
  if (!v.includes("@")) return false;
  const [, domain = ""] = v.split("@");
  return domain.includes(".");
}

export function SponsorTeamInviteModal({
  open,
  sponsorId,
  onClose,
  onInvited,
  onError,
  onSuccess,
}: Props) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [busy, setBusy] = useState(false);

  const canSubmit = isValidEmail(email) && ROLES.some((r) => r.value === role);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) {
      onError("Enter a valid email and choose a role.");
      return;
    }
    setBusy(true);
    try {
      await inviteSponsorTeamMember(sponsorId, {
        email: email.trim().toLowerCase(),
        role,
      });
      setEmail("");
      setRole("viewer");
      onSuccess("Invite sent.");
      await onInvited();
      onClose();
    } catch (err) {
      onError(err instanceof ApiError ? err.detail : "Invite failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Invite team member">
      <form className="space-y-4" onSubmit={(e) => void submit(e)}>
        <label className="block space-y-1 text-sm">
          <span className="font-semibold">Email</span>
          <Input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@company.com"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="font-semibold">Role</span>
          <Select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </Select>
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !canSubmit}>
            {busy ? "Sending…" : "Send invite"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
