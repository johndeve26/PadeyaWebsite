import Link from "next/link";

import { MarketingSection } from "@/components/marketing/MarketingSection";
import { Button } from "@/components/ui";

import { forFansPassportPoints } from "./content";
import { PassportPreview } from "./PassportPreview";

export function FansPassportSection() {
  return (
    <MarketingSection
      id="fan-passport"
      tone="ink-soft"
      eyebrow="Fan Passport"
      title="Your public-safe identity for the scene"
      description="Badges, attended nights, reviews, and a shareable profile, with visibility you control."
    >
      <div className="grid items-center gap-10 lg:grid-cols-[1fr_0.95fr] lg:gap-14">
        <ul className="space-y-6">
          {forFansPassportPoints.map((point) => (
            <li key={point.title} className="border-l-2 border-primary/70 pl-4">
              <p className="text-lg font-extrabold tracking-tight text-paper">
                {point.title}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-paper/70 sm:text-base">
                {point.body}
              </p>
            </li>
          ))}
          <li className="flex flex-col gap-3 pt-2 sm:flex-row">
            <Link
              href="/register?next=/dashboard/passport"
              className="w-full sm:w-auto"
            >
              <Button size="lg" className="w-full sm:w-auto">
                Create Fan Passport
              </Button>
            </Link>
            <Link href="/fans" className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="outline-dark"
                className="w-full sm:w-auto"
              >
                Browse passports
              </Button>
            </Link>
          </li>
        </ul>
        <div className="padeya-fade-up lg:justify-self-end">
          <PassportPreview />
        </div>
      </div>
    </MarketingSection>
  );
}
