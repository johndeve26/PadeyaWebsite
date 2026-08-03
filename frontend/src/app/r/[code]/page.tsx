"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { capturePlatformReferral } from "@/lib/ambassador-referral";
import { apiRequest, ApiError } from "@/lib/api";

type ResolveResult = {
  referral_code: string;
  landing_path: string;
  scope: string;
};

export default function ReferralResolvePage() {
  const params = useParams<{ code: string }>();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = (params?.code || "").trim();
    if (!code) {
      setError("Missing referral code");
      return;
    }
    let active = true;
    void (async () => {
      try {
        const result = await apiRequest<ResolveResult>(
          `/promos/referral/resolve/${encodeURIComponent(code)}`,
          { method: "GET", auth: false },
        );
        if (!active) return;
        capturePlatformReferral(result.referral_code);
        const path = result.landing_path || "/events";
        // Only allow internal redirects
        if (path.startsWith("http://") || path.startsWith("https://")) {
          router.replace("/events");
          return;
        }
        router.replace(path.startsWith("/") ? path : `/${path}`);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.detail
            : "This referral link is invalid or no longer active.",
        );
      }
    })();
    return () => {
      active = false;
    };
  }, [params?.code, router]);

  if (error) {
    return (
      <main className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center gap-4 px-4 py-16 text-center">
        <h1 className="text-2xl font-semibold text-foreground">Link unavailable</h1>
        <p className="text-muted-foreground">{error}</p>
        <a href="/events" className="text-brand underline">
          Browse events
        </a>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-[50vh] max-w-lg items-center justify-center px-4 py-16">
      <p className="text-muted-foreground">Opening your referral link…</p>
    </main>
  );
}
