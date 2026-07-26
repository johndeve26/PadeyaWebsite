import { Container } from "@/components/ui";

/**
 * Stable-height fallback for merch detail Suspense (useSearchParams).
 * Avoids footer.mt-auto CLS when the product shell streams in late.
 */
export function MerchDetailSuspenseFallback() {
  return (
    <main
      className="min-w-0 overflow-x-clip bg-background pb-16"
      aria-busy="true"
      aria-label="Loading product"
    >
      <Container className="py-8 sm:py-12">
        <div className="grid gap-8 lg:grid-cols-2 lg:gap-12">
          <div className="aspect-[4/5] animate-pulse bg-surface-dark" />
          <div className="space-y-4">
            <div className="h-8 w-1/3 animate-pulse rounded bg-surface-inset" />
            <div className="h-12 w-2/3 animate-pulse rounded bg-surface-inset" />
            <div className="h-24 animate-pulse rounded bg-surface-inset" />
            <div className="h-12 w-40 animate-pulse rounded bg-surface-inset" />
          </div>
        </div>
      </Container>
    </main>
  );
}
