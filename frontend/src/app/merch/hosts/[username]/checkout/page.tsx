import { Suspense } from "react";

import { HostShopCheckoutView } from "@/components/merch/marketplace/HostShopCheckoutView";
import { Container, SkeletonLoader } from "@/components/ui";

type PageProps = {
  params: Promise<{ username: string }>;
};

function CheckoutFallback() {
  return (
    <main className="bg-background py-16">
      <Container width="narrow">
        <SkeletonLoader lines={6} />
      </Container>
    </main>
  );
}

export default async function HostShopCheckoutPage({ params }: PageProps) {
  const { username } = await params;
  const clean = decodeURIComponent(username).replace(/^@/, "");
  return (
    <Suspense fallback={<CheckoutFallback />}>
      <HostShopCheckoutView username={clean} />
    </Suspense>
  );
}
