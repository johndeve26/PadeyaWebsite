"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { HostSponsorshipSlotForm } from "@/components/sponsors/HostSponsorshipSlotForm";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { SponsorshipSlotFormValues } from "@/lib/sponsorship-slot-form";
import {
  fetchHostSponsorshipSlots,
  updateSponsorshipSlot,
} from "@/lib/sponsorships-api";
import type { SponsorshipSlot } from "@/lib/types/sponsorships";

export default function EditSponsorshipSlotPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const slotId = params.id;
  const [slot, setSlot] = useState<SponsorshipSlot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchHostSponsorshipSlots();
        if (!active) return;
        const match = rows.find((row) => row.id === slotId) ?? null;
        if (!match) {
          setError("Sponsorship slot not found");
        }
        setSlot(match);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load slot");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [slotId]);

  async function onSubmit(values: SponsorshipSlotFormValues) {
    if (!slot) return;
    setBusy(true);
    setError(null);
    try {
      await updateSponsorshipSlot(slot.id, {
        slot_type: values.slot_type,
        title: values.title,
        description: values.description,
        price: values.price,
      });
      router.push("/host/sponsorships");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        compact
        eyebrow="Sponsorships"
        title="Edit sponsorship package"
        description="Update what brands see. Status changes (publish / disable) stay on the sponsorships list."
        actions={
          <Link href="/host/sponsorships">
            <Button size="sm" variant="secondary">
              Back to sponsorships
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Could not save package">
            {error}
          </Alert>
        ) : null}

        {loading ? (
          <SkeletonLoader lines={6} />
        ) : slot ? (
          <HostSponsorshipSlotForm
            mode="edit"
            initial={{
              slot_type: slot.slot_type,
              title: slot.title,
              description: slot.description,
              price: String(slot.price ?? ""),
            }}
            busy={busy}
            submitLabel="Save changes"
            onSubmit={onSubmit}
          />
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
