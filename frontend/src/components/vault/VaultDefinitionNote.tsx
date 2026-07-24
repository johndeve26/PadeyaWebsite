"use client";

import {
  VAULT_DEFINITION,
  VAULT_EXAMPLES,
  VAULT_UNLOCK_PATHS,
} from "@/lib/vault-copy";
import { cn } from "@/lib/cn";

type Props = {
  /** Show example drop types (host studio / empty states). */
  showExamples?: boolean;
  /** Compact = definition only. */
  compact?: boolean;
  className?: string;
  tone?: "light" | "dark";
};

/**
 * Shared Vault definition for host studio and public surfaces.
 */
export function VaultDefinitionNote({
  showExamples = false,
  compact = false,
  className = "",
  tone = "light",
}: Props) {
  const muted = tone === "dark" ? "text-subtle-foreground" : "text-muted-foreground";
  const strong = tone === "dark" ? "text-paper" : "text-foreground";

  return (
    <div className={cn("space-y-3", className)}>
      <p className={cn("text-sm leading-relaxed sm:text-base", muted)}>
        <span className={cn("font-bold", strong)}>Vault</span>
        {" — "}
        {VAULT_DEFINITION.replace(/^Vault is /, "")}
      </p>
      {!compact ? (
        <p className={cn("text-xs font-semibold uppercase tracking-[0.12em]", muted)}>
          Unlock paths: {VAULT_UNLOCK_PATHS.join(" · ")}
        </p>
      ) : null}
      {showExamples ? (
        <ul className={cn("grid gap-1.5 text-sm sm:grid-cols-2", muted)}>
          {VAULT_EXAMPLES.map((example) => (
            <li key={example} className="flex gap-2">
              <span className="text-accent" aria-hidden>
                ·
              </span>
              <span>{example}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
