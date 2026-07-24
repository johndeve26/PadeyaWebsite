import type { ScanResult } from "@/lib/checkin-api";

export type ScanResultTone = "success" | "warning" | "danger" | "neutral" | "info";

export type ScanResultDisplay = {
  headline: string;
  subline: string;
  tone: ScanResultTone;
  invalidReason?: string;
};

function inferInvalidReason(message: string): string | undefined {
  const m = message.toLowerCase();
  if (m.includes("wrong event")) return "Wrong event";
  if (m.includes("not found") || m.includes("no ticket")) return "Not found";
  if (m.includes("unpaid") || m.includes("payment")) return "Unpaid";
  if (m.includes("refund")) return "Refunded";
  if (m.includes("cancel")) return "Cancelled";
  if (m.includes("transfer")) return "Transferred";
  return undefined;
}

export function describeScanResult(result: ScanResult): ScanResultDisplay {
  const msg = result.message ?? "";

  if (result.outcome === "queued") {
    return {
      headline: "QUEUED OFFLINE",
      subline: "Saved locally — sync when online",
      tone: "info",
    };
  }

  if (result.outcome === "success" || result.outcome === "valid") {
    return {
      headline: "VALID",
      subline: "Guest may enter",
      tone: "success",
    };
  }

  if (result.outcome === "duplicate") {
    return {
      headline: "ALREADY CHECKED IN",
      subline: msg || "This ticket was scanned before",
      tone: "warning",
    };
  }

  if (result.outcome === "invalid") {
    const reason = inferInvalidReason(msg);
    if (reason === "Wrong event") {
      return {
        headline: "WRONG EVENT",
        subline: msg,
        tone: "warning",
        invalidReason: reason,
      };
    }
    return {
      headline: "INVALID TICKET",
      subline: msg || "Do not admit",
      tone: "danger",
      invalidReason: reason ?? "Not accepted",
    };
  }

  return {
    headline: result.outcome.toUpperCase(),
    subline: msg,
    tone: "neutral",
  };
}

export type RecentScanRow = {
  key: string;
  outcome: string;
  holderName: string;
  ticketType: string;
  at: string;
};

export function toRecentScan(result: ScanResult): RecentScanRow {
  return {
    key: `${Date.now()}-${result.ticket?.public_code ?? "scan"}`,
    outcome: result.outcome,
    holderName: result.ticket?.holder_name ?? "Guest",
    ticketType: result.ticket?.ticket_type_name ?? "Ticket",
    at: new Date().toISOString(),
  };
}
