import type { Metadata } from "next";
import { Suspense } from "react";

import { RegisterForm } from "@/components/auth/RegisterForm";
import { Container, SkeletonLoader } from "@/components/ui";
import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Register");

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-[50vh] bg-ink py-20">
          <Container width="narrow">
            <SkeletonLoader lines={4} />
          </Container>
        </main>
      }
    >
      <RegisterForm />
    </Suspense>
  );
}
