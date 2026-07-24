"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { HostSponsorshipSlotForm } from "@/components/sponsors/HostSponsorshipSlotForm";
import { Alert, Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { SponsorshipSlotFormValues } from "@/lib/sponsorship-slot-form";
import { createSponsorshipSlot } from "@/lib/sponsorships-api";

export default function NewSponsorshipSlotPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(values: SponsorshipSlotFormValues) {
    setBusy(true);
    setError(null);
    try {
      await createSponsorshipSlot({
        slot_type: values.slot_type,
        title: values.title,
        description: values.description,
        price: values.price,
        status: values.publish ? "published" : "draft",
      });
      router.push("/host/sponsorships");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
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
        title="Create a sponsorship package"
        description="Write the offer brands will see on Pàdéyá — clear placement, price, and deliverables. Publishing requires a verified host account."
        actions={
          <Link href="/host/sponsorships">
            <Button size="sm" variant="secondary">
              Back to sponsorships
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Could not create package">
            {error}
          </Alert>
        ) : null}

        <HostSponsorshipSlotForm
          mode="create"
          initial={{
            slot_type: "logo_event_page",
            title: "",
            description: "",
            price: "",
            publish: false,
          }}
          busy={busy}
          submitLabel="Save as draft"
          onSubmit={onSubmit}
        />
      </DashboardShell>
    </RequireHost>
  );
}
