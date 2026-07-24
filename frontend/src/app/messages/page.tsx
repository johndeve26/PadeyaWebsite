"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { userHasRole } from "@/lib/auth/permissions";
import { Container } from "@/components/ui";

export default function MessagesRedirectPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login?next=/messages");
      return;
    }
    if (userHasRole(user, "host", "host_staff")) {
      router.replace("/host/messages");
      return;
    }
    router.replace("/dashboard/messages");
  }, [user, loading, router]);

  return (
    <Container className="py-16">
      <p className="text-sm text-muted-foreground">Opening your Pàdéyá inbox…</p>
    </Container>
  );
}
