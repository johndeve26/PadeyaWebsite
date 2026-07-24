import Link from "next/link";

import { Button, Container } from "@/components/ui";
import { cn } from "@/lib/cn";

type Cta = { href: string; label: string };

type MarketingFinalCtaProps = {
  title: string;
  description: string;
  primary: Cta;
  secondary: Cta;
  tertiary?: Cta;
  className?: string;
};

export function MarketingFinalCta({
  title,
  description,
  primary,
  secondary,
  tertiary,
  className = "",
}: MarketingFinalCtaProps) {
  return (
    <section
      className={cn(
        "relative overflow-hidden bg-ink py-20 text-paper sm:py-24",
        className,
      )}
    >
      <div
        aria-hidden
        className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-90"
      />
      <div
        aria-hidden
        className="padeya-grain pointer-events-none absolute inset-0 opacity-35"
      />
      <Container className="relative flex flex-col items-stretch gap-8 sm:flex-row sm:items-center sm:justify-between sm:gap-10">
        <div className="max-w-2xl space-y-3">
          <h2 className="text-balance text-3xl font-extrabold tracking-tight [text-shadow:0_2px_28px_rgb(0_0_0_/0.55)] sm:text-4xl md:text-[2.5rem] md:leading-[1.12]">
            {title}
          </h2>
          <p className="max-w-xl text-base leading-relaxed text-paper/75 sm:text-lg">
            {description}
          </p>
        </div>
        <div className="flex w-full shrink-0 flex-col gap-3 sm:w-auto sm:flex-row sm:flex-wrap">
          <Link href={primary.href} className="w-full sm:w-auto">
            <Button size="lg" className="padeya-btn-micro w-full sm:w-auto">
              {primary.label}
            </Button>
          </Link>
          <Link href={secondary.href} className="w-full sm:w-auto">
            <Button
              size="lg"
              variant="outline-dark"
              className="padeya-btn-micro w-full sm:w-auto"
            >
              {secondary.label}
            </Button>
          </Link>
          {tertiary ? (
            <Link href={tertiary.href} className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="ghost"
                className="w-full text-paper hover:bg-paper/10 sm:w-auto"
              >
                {tertiary.label}
              </Button>
            </Link>
          ) : null}
        </div>
      </Container>
    </section>
  );
}
