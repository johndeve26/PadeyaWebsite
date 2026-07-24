"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Button,
  SectionHeader,
  SkeletonLoader,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import {
  adminSponsorNotes,
  adminSponsorStatus,
  adminVerifySponsor,
  fetchAdminSponsorDetail,
  type SponsorAdminDetail,
} from "@/lib/sponsor-profiles-api";

export default function AdminSponsorDetailPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const { user } = useAuth();
  const canView = userHasPermission(user, "admin.sponsors.view");
  const canVerify = userHasPermission(user, "admin.sponsors.verify");
  const canRestrict = userHasPermission(user, "admin.sponsors.restrict");
  const canModerate = userHasPermission(user, "admin.sponsors.moderate");

  const [detail, setDetail] = useState<SponsorAdminDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!params.id) return;
    setDetail(await fetchAdminSponsorDetail(params.id));
    setNotes((prev) => prev || "");
  }, [params.id]);

  useEffect(() => {
    if (!canView || !params.id) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load sponsor");
      }
    })();
  }, [canView, load, params.id]);

  useEffect(() => {
    if (detail?.internal_notes != null && !notes) {
      setNotes(detail.internal_notes);
    }
  }, [detail, notes]);

  if (!canView) {
    return (
      <Alert tone="danger" title="Access denied">
        admin.sponsors.view required.
      </Alert>
    );
  }

  async function verify(action: "approve" | "reject") {
    if (!params.id || !canVerify) return;
    setBusy(true);
    try {
      const updated = await adminVerifySponsor(params.id, action, notes || undefined);
      setDetail(updated);
      toast.push({
        tone: "success",
        title: action === "approve" ? "Sponsor verified" : "Sponsor rejected",
      });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Action failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function restrict() {
    if (!params.id || !canRestrict) return;
    setBusy(true);
    try {
      const updated = await adminSponsorStatus(
        params.id,
        "restricted",
        notes || undefined,
      );
      setDetail(updated);
      toast.push({ tone: "success", title: "Sponsor restricted" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Action failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function saveNotes() {
    if (!params.id || !canModerate) return;
    setBusy(true);
    try {
      const updated = await adminSponsorNotes(params.id, notes || null);
      setDetail(updated);
      toast.push({ tone: "success", title: "Notes saved" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Save failed",
      });
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <Alert tone="danger" title="Error">
        {error}
      </Alert>
    );
  }

  if (!detail) return <SkeletonLoader />;

  return (
    <div className="space-y-6 max-w-2xl">
      <SectionHeader
        eyebrow="Sponsor"
        title={detail.display_name}
        description={`@${detail.slug ?? "—"} · ${detail.verification_status} · ${detail.status}`}
      />
      <dl className="grid gap-2 text-sm">
        <div>
          <dt className="text-muted-foreground">Owner</dt>
          <dd>{detail.owner_email ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Type</dt>
          <dd>{detail.sponsor_type ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Industry</dt>
          <dd>{detail.industry ?? "—"}</dd>
        </div>
      </dl>
      {canModerate ? (
        <label className="block space-y-1 text-sm">
          <span className="font-semibold">Internal notes</span>
          <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
          <Button disabled={busy} variant="secondary" onClick={() => void saveNotes()}>
            Save notes
          </Button>
        </label>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {canVerify ? (
          <>
            <Button disabled={busy} onClick={() => void verify("approve")}>
              Approve verification
            </Button>
            <Button
              disabled={busy}
              variant="secondary"
              onClick={() => void verify("reject")}
            >
              Reject
            </Button>
          </>
        ) : null}
        {canRestrict ? (
          <Button disabled={busy} variant="ghost" onClick={() => void restrict()}>
            Restrict sponsor
          </Button>
        ) : null}
      </div>
    </div>
  );
}
