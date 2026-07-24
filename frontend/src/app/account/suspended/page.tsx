"use client";

import { SuspendedAccountPage } from "@/components/account/SuspendedAccountPage";
import { RequireAuth } from "@/components/auth/RequireAuth";

/** Dedicated suspended account surface (also shown via RequireAuth gate). */
export default function AccountSuspendedRoute() {
  return (
    <RequireAuth>
      <SuspendedAccountPage />
    </RequireAuth>
  );
}
