/** Client-side parse for admin template recipient preview (mirrors backend rules). */

const EMAIL_RE =
  /^[a-z0-9][a-z0-9._+\-]*@[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}$/i;

export const MAX_ADMIN_TEMPLATE_RECIPIENTS = 20;
export const MAX_ADMIN_TEST_RECIPIENTS = 5;

export type RecipientMode = "group" | "custom" | "group_and_custom";

export function parseRecipientEmailsInput(
  raw: string,
  maxCount = MAX_ADMIN_TEMPLATE_RECIPIENTS,
): { emails: string[]; error: string | null } {
  const text = raw.trim();
  if (!text) {
    return { emails: [], error: null };
  }
  const normalized = text.replace(/;/g, ",");
  const parts = normalized.split(",").map((p) => p.trim());
  const out: string[] = [];
  const seen = new Set<string>();

  for (const part of parts) {
    if (!part) continue;
    const email = part.toLowerCase();
    if (!EMAIL_RE.test(email)) {
      return { emails: [], error: `Invalid email: ${part}` };
    }
    if (seen.has(email)) continue;
    seen.add(email);
    out.push(email);
    if (out.length > maxCount) {
      return {
        emails: [],
        error: `At most ${maxCount} recipient emails allowed per template.`,
      };
    }
  }
  return { emails: out, error: null };
}

export function estimateResolvedRecipientCount(params: {
  mode: RecipientMode;
  customEmails: string[];
  serverResolvedCount: number;
  savedCustomCount: number;
}): number {
  const { mode, customEmails, serverResolvedCount, savedCustomCount } = params;
  if (mode === "custom") {
    return customEmails.length;
  }
  if (mode === "group") {
    return serverResolvedCount;
  }
  const groupEstimate = Math.max(0, serverResolvedCount - savedCustomCount);
  const merged = new Set<string>(customEmails);
  return merged.size + groupEstimate;
}
