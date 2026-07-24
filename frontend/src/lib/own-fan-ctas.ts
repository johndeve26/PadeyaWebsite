/**
 * Own Fan Passport vs visitor CTA decisions for Pàdéyá public fan pages.
 *
 * Ownership: isOwnPassport = currentUserId === passportOwnerUserId
 *
 * Own passport hides fan-to-fan actions and shows manage/share CTAs instead.
 * Public content (header, seal, stats, stamps, badges, reviews, vault titles)
 * stays visible either way.
 */

export type FanPageCtaMode = "own_passport" | "visitor";

/** Prefer user ids. Do not rely on username string comparison. */
export function isOwnFanPassport(
  currentUserId: string | null | undefined,
  passportOwnerUserId: string | null | undefined,
): boolean {
  const a = (currentUserId || "").trim().toLowerCase();
  const b = (passportOwnerUserId || "").trim().toLowerCase();
  return Boolean(a && b && a === b);
}

export function fanPageCtaMode(isOwnPassport: boolean): FanPageCtaMode {
  return isOwnPassport ? "own_passport" : "visitor";
}

export function fanPageCtas(mode: FanPageCtaMode) {
  if (mode === "own_passport") {
    return {
      title: "This is your Fan Passport" as const,
      description:
        "Preview how your public fan identity appears on Pàdéyá." as const,
      /** @deprecated use title */
      banner: "This is your Fan Passport" as const,
      primary: {
        label: "Edit Passport" as const,
        href: "/dashboard/passport/settings",
      },
      secondary: {
        label: "Personal dashboard" as const,
        href: "/dashboard",
      },
      share: {
        label: "Share profile" as const,
      },
      showConnect: false,
      showMessage: false,
      showFollow: false,
      showReport: false,
      showBlock: false,
      showConnectionRequest: false,
      showFanToFanMessage: false,
      allowShare: true,
      allowPreview: true,
      allowEdit: true,
    };
  }
  return {
    title: null,
    description: null,
    banner: null,
    primary: null,
    secondary: null,
    share: null,
    showConnect: true,
    showMessage: true,
    showFollow: true,
    showReport: true,
    showBlock: true,
    showConnectionRequest: true,
    showFanToFanMessage: true,
    allowShare: true,
    allowPreview: true,
    allowEdit: false,
  };
}

/** Directory card CTAs — own card shows You / Edit / View only. */
export function directoryCardCtas(
  isOwnPassport: boolean,
  sharePath: string,
) {
  if (isOwnPassport) {
    return {
      youBadge: "You" as const,
      showConnect: false,
      showMessage: false,
      showReport: false,
      showBlock: false,
      edit: {
        label: "Edit Passport" as const,
        href: "/dashboard/passport/settings",
      },
      view: {
        label: "View Passport" as const,
        href: sharePath,
      },
    };
  }
  return {
    youBadge: null,
    showConnect: true,
    showMessage: true,
    showReport: true,
    showBlock: true,
    edit: null,
    view: {
      label: "View Passport" as const,
      href: sharePath,
    },
  };
}
