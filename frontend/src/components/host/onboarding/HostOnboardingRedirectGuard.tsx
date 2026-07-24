"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { SkeletonLoader } from "@/components/ui";
import { fetchMyHost } from "@/lib/hosts-api";

/** Conditional 302 — existing hosts skip the become-a-host form (client guard; auth is localStorage). */
export function HostOnboardingRedirectGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [hasHost, setHasHost] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchMyHost().then((host) => {
      if (cancelled) return;
      if (host) {
        setHasHost(true);
        router.replace("/host/roadmap");
        return;
      }
      setChecking(false);
    });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (checking || hasHost) {
    return (
      <div className="py-16 sm:py-20">
        <SkeletonLoader lines={6} />
      </div>
    );
  }

  return <>{children}</>;
}
