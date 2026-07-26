import { Container } from "@/components/ui";

/**
 * Stable-height fallback for event detail Suspense (useSearchParams).
 * `fallback={null}` let footer.mt-auto sit in the viewport → intermittent CLS.
 */
export function EventDetailSuspenseFallback() {
  return (
    <main className="bg-background" aria-busy="true" aria-label="Loading event">
      <div className="h-[42vh] min-h-[240px] animate-pulse bg-surface-dark sm:h-[52vh] sm:min-h-[320px]" />
      <Container className="relative -mt-20 space-y-8 pb-10 sm:-mt-24">
        <div className="h-44 animate-pulse rounded-[var(--radius-xl)] border border-border bg-card sm:h-52" />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-4">
            <div className="h-40 animate-pulse rounded-[var(--radius-xl)] bg-surface-inset" />
            <div className="h-56 animate-pulse rounded-[var(--radius-xl)] bg-surface-inset" />
          </div>
          <div className="h-64 animate-pulse rounded-[var(--radius-xl)] bg-surface-inset" />
        </div>
      </Container>
    </main>
  );
}
