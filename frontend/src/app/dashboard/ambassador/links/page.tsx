"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AmbassadorDashNav } from "@/components/ambassadors/AmbassadorDashNav";
import { AmbassadorShareCard } from "@/components/ambassadors/AmbassadorShareCard";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  buildAmbassadorEventLink,
  buildAmbassadorReferralLink,
  formatAmbassadorCodeDisplay,
} from "@/lib/ambassador-referral";
import { fetchMyAmbassadorEnrollments } from "@/lib/promos-api";
import type { AmbassadorDashboard } from "@/lib/types/promos";

export default function AmbassadorLinksPage() {
  const [enrollments, setEnrollments] = useState<AmbassadorDashboard[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyAmbassadorEnrollments();
        if (active) {
          setEnrollments(
            data.enrollments.filter((e) => e.ambassador.status === "active"),
          );
          setLoaded(true);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Could not load links");
          setLoaded(true);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function copy(id: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(id);
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      setError("Could not copy — select the text manually");
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Ambassadors"
      title="Ambassador links"
      description="Copy your unique code or link. Codes are unique per campaign. Referral cookies last 30 days (last click wins)."
    >
      <AmbassadorDashNav />

      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      {!loaded ? <SkeletonLoader lines={4} /> : null}

      {loaded && enrollments.length === 0 && !error ? (
        <EmptyState
          title="No Ambassador links yet"
          description="Promote an eligible event to generate your first link and code."
          action={
            <Link href="/ambassadors/events">
              <Button size="sm">Browse eligible events</Button>
            </Link>
          }
        />
      ) : null}

      {enrollments.map((data) => {
        const amb = data.ambassador;
        const slug = amb.event_slug;
        const code = amb.referral_code;
        const display =
          amb.referral_code_display || formatAmbassadorCodeDisplay(code);
        const isMerch = amb.campaign_type === "event_merch";
        const link = buildAmbassadorReferralLink(code, {
          slug,
          merch: isMerch,
        });
        const eventLink = slug
          ? buildAmbassadorEventLink(slug, code)
          : link;
        return (
          <Card key={amb.id} className="space-y-4">
            <div>
              <h2 className="text-lg font-bold">
                {amb.event_title || amb.display_name}
              </h2>
              {amb.campaign_type_label ? (
                <p className="text-sm text-muted-foreground">
                  {amb.campaign_type_label}
                </p>
              ) : null}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Ambassador code
              </p>
              <p className="mt-1 font-mono text-base font-bold tracking-wide">
                {display}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {isMerch ? "Merch referral link" : "Event referral link"}
              </p>
              <p className="mt-1 break-all text-sm text-body">{link}</p>
              {isMerch && slug ? (
                <p className="mt-2 break-all text-xs text-muted-foreground">
                  Event page also works: {eventLink}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void copy(`${amb.id}-link`, link)}
              >
                {copied === `${amb.id}-link` ? "Copied link" : "Copy link"}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void copy(`${amb.id}-code`, display)}
              >
                {copied === `${amb.id}-code` ? "Copied code" : "Copy code"}
              </Button>
            </div>
            {slug ? (
              <AmbassadorShareCard
                eventTitle={amb.event_title || "Pàdéyá event"}
                code={code}
                link={link}
                campaignLabel={amb.campaign_type_label}
              />
            ) : null}
          </Card>
        );
      })}
    </DashboardShell>
  );
}
