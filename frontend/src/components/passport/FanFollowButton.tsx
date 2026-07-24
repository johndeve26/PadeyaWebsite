"use client";

import { fanPageCtas } from "@/lib/own-fan-ctas";

type FanCtas = ReturnType<typeof fanPageCtas>;

/**
 * Fan↔fan Follow CTA for public Passport / directory cards.
 *
 * Always hidden on own Passport (`isOwnPassport` / `showFollow === false`).
 * Backend self-follow is denied with: “You can’t follow yourself.”
 *
 * Fan-to-fan follow is not product-ready yet — visitors also get no button
 * until the mutation ships. Keep mounting this behind ``showFollow`` so
 * own-page stays gated by default.
 */
export function FanFollowButton({
  isOwnPassport = false,
  showFollow,
  ctas,
}: {
  isOwnPassport?: boolean;
  showFollow?: boolean;
  ctas?: FanCtas;
  size?: "sm" | "md" | "lg";
  className?: string;
  targetUserId?: string | null;
}) {
  if (isOwnPassport) return null;

  const resolved = ctas ?? fanPageCtas("visitor");
  if ((showFollow ?? resolved.showFollow) !== true) return null;

  // Feature not shipped — avoid a dead Follow CTA for visitors.
  return null;
}
