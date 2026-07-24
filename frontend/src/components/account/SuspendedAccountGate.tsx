"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth/AuthProvider";
import { Alert, Button, Container } from "@/components/ui";

/**
 * Blocks nested product UI when the session is suspended/banned.
 * Suspended users get Logout + Appeal; does not expose admin internals.
 */
export function SuspendedAccountGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();

  if (loading || !user) return <>{children}</>;

  const status = (user.account_status || "").toLowerCase();
  const blocked =
    status === "suspended" ||
    status === "banned" ||
    user.is_active === false;

  if (!blocked) return <>{children}</>;

  if (status === "suspended") {
    return (
      <main className="bg-background py-16 sm:py-20">
        <Container width="narrow" className="space-y-4">
          <Alert tone="danger" title="Account suspended">
            Your account is suspended. You can review details and submit an
            appeal, or sign out.
          </Alert>
          <div className="flex flex-wrap gap-2">
            <Link href="/account/suspended">
              <Button size="sm">Appeal</Button>
            </Link>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => void logout()}
            >
              Log out
            </Button>
          </div>
        </Container>
      </main>
    );
  }

  return (
    <main className="bg-background py-16 sm:py-20">
      <Container width="narrow" className="space-y-4">
        <Alert tone="danger" title="Account banned">
          This action isn’t available on your account. If you believe this is a
          mistake, contact Pàdéyá support.
        </Alert>
        <div className="flex flex-wrap gap-2">
          <Link href="/">
            <Button variant="secondary" size="sm">
              Back to home
            </Button>
          </Link>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => void logout()}
          >
            Log out
          </Button>
        </div>
      </Container>
    </main>
  );
}
