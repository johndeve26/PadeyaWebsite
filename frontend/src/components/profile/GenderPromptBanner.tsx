"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Alert, Button } from "@/components/ui";
import { GENDER_PROMPT_DISMISS_KEY } from "@/lib/gender";

type Props = {
  className?: string;
};

/**
 * Soft prompt for legacy accounts with unset gender. Dismiss is local-only.
 */
export function GenderPromptBanner({ className = "" }: Props) {
  const { user, loading } = useAuth();
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    try {
      setDismissed(
        window.localStorage.getItem(GENDER_PROMPT_DISMISS_KEY) === "1",
      );
    } catch {
      setDismissed(false);
    }
  }, []);

  if (loading || !user || user.gender != null || dismissed) {
    return null;
  }

  function onDismiss() {
    try {
      window.localStorage.setItem(GENDER_PROMPT_DISMISS_KEY, "1");
    } catch {
      // ignore quota / private mode
    }
    setDismissed(true);
  }

  return (
    <Alert tone="info" title="Add gender to your profile" className={className}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-relaxed">
          Help connections recognize you on Pàdéyá. You control who can see it —
          public, connections only, or private.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/passport/settings">
            <Button type="button" size="sm">
              Add gender
            </Button>
          </Link>
          <Button type="button" size="sm" variant="ghost" onClick={onDismiss}>
            Dismiss
          </Button>
        </div>
      </div>
    </Alert>
  );
}
