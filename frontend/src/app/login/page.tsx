import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";
import { Container, SkeletonLoader } from "@/components/ui";

export const metadata = { title: "Log in" };

export default function LoginPage() {
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
      <LoginForm />
    </Suspense>
  );
}
