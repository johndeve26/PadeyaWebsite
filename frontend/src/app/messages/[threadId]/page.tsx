"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { userHasRole } from "@/lib/auth/permissions";
import { Container } from "@/components/ui";

export default function MessagesThreadRedirectPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams<{ threadId: string }>();

  useEffect(() => {
    if (loading || !params?.threadId) return;
    if (!user) {
      router.replace(`/login?next=/messages/${params.threadId}`);
      return;
    }
    if (userHasRole(user, "host", "host_staff")) {
      router.replace(`/host/messages/${params.threadId}`);
      return;
    }
    router.replace(`/dashboard/messages/${params.threadId}`);
  }, [user, loading, router, params?.threadId]);

  return (
    <Container className="py-16">
      <p className="text-sm text-muted-foreground">Opening conversation…</p>
    </Container>
  );
}
