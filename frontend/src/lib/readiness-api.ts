import { apiRequest } from "@/lib/api";

export type ReadinessCheckStatus = "pass" | "fail" | "warn" | "skip";

export type ReadinessCheck = {
  id: string;
  category: string;
  name: string;
  status: ReadinessCheckStatus;
  message: string;
  fix: string | null;
  details: Record<string, unknown>;
};

export type ProductionReadinessReport = {
  verdict: "READY_FOR_PRODUCTION" | "BLOCKED";
  summary: string;
  checks: ReadinessCheck[];
  ai_readiness?: AIReadinessSummary | null;
};

export type AIReadinessSummary = {
  status: "PASS" | "WARN" | "FAIL";
  templates_seeded: boolean;
  feature_routes_present: boolean;
  provider_status: string;
  kill_switch_active: boolean;
  blocked_keys_status: string;
  quarantined_keys_status: string;
  spend_cap_status: string;
  message: string;
};

export async function fetchProductionReadiness(): Promise<ProductionReadinessReport> {
  return apiRequest<ProductionReadinessReport>("/admin/platform/readiness");
}
