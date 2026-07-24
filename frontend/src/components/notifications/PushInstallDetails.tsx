"use client";

import { IOS_PUSH_HELPER } from "@/lib/push-device";

type Props = {
  /** iPhone/iPad Home Screen steps vs generic install tip */
  variant?: "ios" | "generic";
  className?: string;
};

/**
 * Expandable install help — keeps the settings card short.
 */
export function PushInstallDetails({
  variant = "ios",
  className = "",
}: Props) {
  return (
    <details
      className={`min-w-0 rounded-md border border-border bg-muted/30 open:bg-muted/40 ${className}`}
    >
      <summary className="cursor-pointer list-outside px-3 py-2.5 text-sm font-semibold text-foreground marker:text-muted-foreground">
        How to install
      </summary>
      <div className="space-y-2 border-t border-border px-3 py-3 text-sm text-muted-foreground">
        {variant === "ios" ? (
          <>
            <p className="text-foreground">{IOS_PUSH_HELPER.body}</p>
            <ol className="list-decimal space-y-1.5 pl-4">
              {IOS_PUSH_HELPER.steps.map((step) => (
                <li key={step} className="leading-snug">
                  {step}
                </li>
              ))}
            </ol>
            <p className="text-xs leading-relaxed">{IOS_PUSH_HELPER.browsersNote}</p>
            <p className="text-xs leading-relaxed">{IOS_PUSH_HELPER.whyNote}</p>
          </>
        ) : (
          <>
            <p>
              On desktop or Android, use your browser’s install or Add to Home
              screen option when offered, then open Pàdéyá from that icon.
            </p>
            <p className="text-xs leading-relaxed">
              On iPhone or iPad: Share or browser menu → Add to Home Screen →
              open from the Home Screen icon → enable notifications.
            </p>
          </>
        )}
      </div>
    </details>
  );
}
