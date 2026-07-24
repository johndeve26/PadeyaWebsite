"use client";

import { cn } from "@/lib/cn";

import {
  MERCH_FORM_SECTIONS,
  type MerchFormSectionId,
  type MerchSectionStatus,
} from "./types";

type Props = {
  active: MerchFormSectionId;
  onChange: (id: MerchFormSectionId) => void;
  statuses: Record<MerchFormSectionId, MerchSectionStatus>;
};

const STATUS_SHORT: Record<MerchSectionStatus, string> = {
  complete: "Complete",
  needs_info: "Needs info",
  optional: "Optional",
};

export function MerchFormStepper({ active, onChange, statuses }: Props) {
  const activeIndex = MERCH_FORM_SECTIONS.findIndex((s) => s.id === active);
  const activeStatus = statuses[active];

  return (
    <div className="space-y-2">
      <nav aria-label="Merch form sections">
        <ol className="-mx-1 flex min-w-0 items-center gap-0.5 overflow-x-auto px-1 pb-0.5 [scrollbar-width:thin]">
          {MERCH_FORM_SECTIONS.map((section, index) => {
            const status = statuses[section.id];
            const isActive = active === section.id;
            const isComplete = status === "complete";
            const isPast = index < activeIndex;

            return (
              <li key={section.id} className="flex shrink-0 items-center">
                {index > 0 ? (
                  <span
                    aria-hidden
                    className={cn(
                      "mx-0.5 hidden h-px w-2.5 shrink-0 sm:block",
                      isPast || isComplete ? "bg-primary/40" : "bg-border",
                    )}
                  />
                ) : null}
                <button
                  type="button"
                  onClick={() => onChange(section.id)}
                  aria-current={isActive ? "step" : undefined}
                  aria-label={`${section.label}, step ${index + 1}${
                    isActive ? `, ${STATUS_SHORT[status]}` : ""
                  }`}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full border px-2 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isActive
                      ? "border-primary bg-[color-mix(in_srgb,var(--primary)_12%,transparent)] text-foreground"
                      : isComplete
                        ? "border-border bg-card text-foreground hover:border-primary/30"
                        : "border-border bg-muted/30 text-muted-foreground hover:border-border-strong/25 hover:text-foreground",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-extrabold leading-none",
                      isActive
                        ? "bg-ink text-primary"
                        : isComplete
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground",
                    )}
                  >
                    {isComplete && !isActive ? "✓" : index + 1}
                  </span>
                  <span className="whitespace-nowrap text-xs font-semibold leading-none">
                    {section.compactLabel}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      <p className="text-xs text-muted-foreground" aria-live="polite">
        <span className="font-semibold text-foreground">
          {MERCH_FORM_SECTIONS[activeIndex]?.label}
        </span>
        <span className="mx-1.5 text-border">·</span>
        {STATUS_SHORT[activeStatus]}
        {active === "review" ? (
          <>
            <span className="mx-1.5 text-border">·</span>
            {MERCH_FORM_SECTIONS.filter((s) => statuses[s.id] === "complete").length}{" "}
            of {MERCH_FORM_SECTIONS.length - 1} sections ready
          </>
        ) : null}
      </p>
    </div>
  );
}
