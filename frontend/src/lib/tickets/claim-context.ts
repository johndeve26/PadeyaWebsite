import { apiRequest } from "@/lib/api";

export type TransferClaimContext = {
  recipient_email: string;
  recipient_name?: string | null;
  event_title?: string | null;
  status: string;
};

export function parseClaimTokenFromPath(pathOrNext: string | null): string | null {
  if (!pathOrNext) return null;
  const trimmed = pathOrNext.trim();
  const queryStart = trimmed.indexOf("?");
  if (queryStart === -1) return null;
  const params = new URLSearchParams(trimmed.slice(queryStart + 1));
  const token = params.get("token")?.trim().slice(0, 200) ?? "";
  if (!/^[A-Za-z0-9_\-]+$/.test(token)) return null;
  return token;
}

export function parseEmailFromClaimPath(pathOrNext: string | null): string | null {
  if (!pathOrNext) return null;
  const trimmed = pathOrNext.trim();
  const queryStart = trimmed.indexOf("?");
  if (queryStart === -1) return null;
  const params = new URLSearchParams(trimmed.slice(queryStart + 1));
  const email = params.get("email")?.trim().toLowerCase() ?? "";
  if (!email || !email.includes("@")) return null;
  return email;
}

export function resolveRegisterEmailFromSearchParams(
  params: URLSearchParams,
): { email: string; token: string | null } {
  const direct = params.get("email")?.trim().toLowerCase() ?? "";
  const next = params.get("next");
  const fromNext = parseEmailFromClaimPath(next);
  const email = direct || fromNext || "";
  const token =
    parseClaimTokenFromPath(next) ||
    (params.get("token") ? parseClaimTokenFromPath(`?token=${params.get("token")}`) : null);
  return { email, token };
}

export async function fetchTransferClaimContext(
  token: string,
): Promise<TransferClaimContext> {
  const q = encodeURIComponent(token);
  return apiRequest<TransferClaimContext>(`/tickets/claim/context?token=${q}`, {
    auth: false,
  });
}
