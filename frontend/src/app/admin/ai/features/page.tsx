"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  AIControlCenterHeader,
  AIControlCenterNav,
} from "@/components/admin/ai/AIControlCenterNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Drawer,
  Modal,
  Select,
  SkeletonLoader,
  Switch,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  AUTO_MODEL,
  formValueToRouteModel,
  modelOptionsForProvider,
  routeModelToFormValue,
} from "@/lib/ai-model-catalog";
import {
  fetchAIFeatureRoutes,
  fetchAIProviderProfiles,
  updateAIFeatureRoute,
} from "@/lib/ai-api";
import type { AIFeatureRoute, AIFeatureReadiness } from "@/lib/types/ai";

const DOCS_AUDIT_PATH = "docs/AI_FEATURE_STATUS_AUDIT.md";

type SectionDef = {
  id: string;
  title: string;
  description?: string;
  filter: (row: AIFeatureRoute) => boolean;
};

const SECTIONS: SectionDef[] = [
  {
    id: "host",
    title: "Active Host features",
    filter: (r) => !r.future && r.category === "host" && r.product_status === "active",
  },
  {
    id: "fan",
    title: "Active Fan features",
    description: "Fan-facing draft AI (Passport and related).",
    filter: (r) =>
      !r.future && r.category === "fan" && r.product_status === "active",
  },
  {
    id: "support",
    title: "Active Support features",
    filter: (r) => !r.future && r.category === "support" && r.product_status === "active",
  },
  {
    id: "admin",
    title: "Active Admin features",
    filter: (r) => !r.future && r.category === "admin" && r.product_status === "active",
  },
  {
    id: "blog",
    title: "Active Blog features",
    filter: (r) => !r.future && r.category === "blog" && r.product_status === "active",
  },
  {
    id: "platform",
    title: "Active Platform features",
    description: "Site-wide conversational assistant (Ask Pàdéyá / Pàdéyá Copilot).",
    filter: (r) =>
      !r.future && r.category === "platform" && r.product_status === "active",
  },
  {
    id: "future",
    title: "Future & planned AI",
    description:
      "Registry placeholders only — not connected to generation or product UI.",
    filter: (r) => r.future && r.product_status !== "blocked",
  },
  {
    id: "blocked",
    title: "Blocked by safety",
    description: "Requires product and safety review before any implementation work.",
    filter: (r) => r.product_status === "blocked",
  },
];

function productBadge(row: AIFeatureRoute) {
  switch (row.product_status) {
    case "active":
      return <Badge tone="accent">Active</Badge>;
    case "future":
      return <Badge tone="outline">Future</Badge>;
    case "partial":
      return <Badge tone="warning">Partial</Badge>;
    case "blocked":
      return <Badge tone="danger">Blocked by safety</Badge>;
    case "deprecated":
      return <Badge tone="neutral">Deprecated</Badge>;
    default:
      return <Badge tone="outline">{row.product_status}</Badge>;
  }
}

function operationalBadge(row: AIFeatureRoute) {
  switch (row.operational_status) {
    case "on":
      return <Badge tone="accent">On</Badge>;
    case "off":
      return <Badge tone="warning">Off</Badge>;
    case "needs_configuration":
      return <Badge tone="warning">Needs configuration</Badge>;
    case "not_available":
      return <Badge tone="outline">Not available</Badge>;
    default:
      return <Badge tone="outline">{row.operational_status}</Badge>;
  }
}

const READINESS_LABELS: { key: keyof AIFeatureReadiness; label: string }[] = [
  { key: "backend_allowlist", label: "Backend generate allowlist" },
  { key: "prompt_template", label: "Prompt template" },
  { key: "context_builder", label: "Context builder" },
  { key: "redaction_rules", label: "Redaction rules" },
  { key: "output_validation", label: "Output validation" },
  { key: "frontend_ui", label: "Frontend UI" },
  { key: "audit_usage_logging", label: "Audit / usage logging" },
  { key: "safe_to_enable", label: "Safe to enable" },
];

function ReadinessChecklist({ readiness }: { readiness: AIFeatureReadiness }) {
  return (
    <ul className="space-y-2 text-sm">
      {READINESS_LABELS.map(({ key, label }) => (
        <li key={key} className="flex items-center justify-between gap-3 border-b border-border pb-1">
          <span>{label}</span>
          {readiness[key] ? (
            <Badge tone="accent">Ready</Badge>
          ) : (
            <Badge tone="outline">Not ready</Badge>
          )}
        </li>
      ))}
    </ul>
  );
}

function FeatureTable({
  rows,
  onEdit,
  onDetails,
}: {
  rows: AIFeatureRoute[];
  onEdit: (row: AIFeatureRoute) => void;
  onDetails: (row: AIFeatureRoute) => void;
}) {
  if (!rows.length) {
    return (
      <p className="text-sm text-muted-foreground px-1 py-2">No features in this group.</p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[960px] text-left text-sm">
        <thead className="bg-surface-muted text-muted-foreground">
          <tr>
            <th className="px-3 py-2">Feature</th>
            <th className="px-3 py-2">Product status</th>
            <th className="px-3 py-2">Operational</th>
            <th className="px-3 py-2">Primary</th>
            <th className="px-3 py-2">Fallback</th>
            <th className="px-3 py-2">Review</th>
            <th className="px-3 py-2">Last used</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.feature_key} className="border-t border-border">
              <td className="px-3 py-2">
                <p className="font-semibold">{row.label}</p>
                <p className="text-xs text-muted-foreground">{row.feature_key}</p>
                {row.safety_review_required && row.safety_note ? (
                  <p className="mt-1 text-xs text-amber-800 dark:text-amber-200">
                    {row.safety_note}
                  </p>
                ) : null}
              </td>
              <td className="px-3 py-2">{productBadge(row)}</td>
              <td className="px-3 py-2">{operationalBadge(row)}</td>
              <td className="px-3 py-2 text-muted-foreground">
                {row.routing_editable ? (
                  <>
                    {row.primary_provider_name ?? "—"}
                    <br />
                    <span className="text-xs">
                      {row.primary_model_label ?? row.primary_model ?? "All (auto)"}
                    </span>
                  </>
                ) : (
                  <span className="text-xs">—</span>
                )}
              </td>
              <td className="px-3 py-2 text-muted-foreground">
                {row.routing_editable ? row.fallback_provider_name ?? "—" : "—"}
              </td>
              <td className="px-3 py-2">
                {row.requires_human_review ? "Required" : "Optional"}
              </td>
              <td className="px-3 py-2 text-xs text-muted-foreground">
                {row.last_used_at
                  ? new Date(row.last_used_at).toLocaleString()
                  : "—"}
              </td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  <Button size="sm" variant="ghost" onClick={() => onDetails(row)}>
                    Details
                  </Button>
                  {row.routing_editable ? (
                    <Button size="sm" variant="secondary" onClick={() => onEdit(row)}>
                      Edit routing
                    </Button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminAIFeaturesPage() {
  const [routes, setRoutes] = useState<AIFeatureRoute[]>([]);
  const [providers, setProviders] = useState<
    Awaited<ReturnType<typeof fetchAIProviderProfiles>>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [edit, setEdit] = useState<AIFeatureRoute | null>(null);
  const [details, setDetails] = useState<AIFeatureRoute | null>(null);
  const [primaryId, setPrimaryId] = useState("");
  const [primaryModel, setPrimaryModel] = useState("");
  const [fallbackId, setFallbackId] = useState("");
  const [fallbackModel, setFallbackModel] = useState("");
  const [templateFb, setTemplateFb] = useState(true);
  const [enabled, setEnabled] = useState(true);

  const load = useCallback(async () => {
    const [r, p] = await Promise.all([
      fetchAIFeatureRoutes(),
      fetchAIProviderProfiles(),
    ]);
    setRoutes(r);
    setProviders(p);
  }, []);

  useEffect(() => {
    void load()
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load routing"),
      )
      .finally(() => setLoading(false));
  }, [load]);

  const sectionRows = useMemo(() => {
    const map: Record<string, AIFeatureRoute[]> = {};
    for (const sec of SECTIONS) {
      map[sec.id] = routes.filter(sec.filter);
    }
    return map;
  }, [routes]);

  function openEdit(row: AIFeatureRoute) {
    if (!row.routing_editable) return;
    setEdit(row);
    setPrimaryId(row.primary_provider_id ?? "");
    setPrimaryModel(routeModelToFormValue(row.primary_model));
    setFallbackId(row.fallback_provider_id ?? "");
    setFallbackModel(routeModelToFormValue(row.fallback_model));
    setTemplateFb(row.template_fallback_enabled);
    setEnabled(row.enabled);
  }

  const primaryProvider = providers.find((p) => p.id === primaryId);
  const fallbackProvider = providers.find((p) => p.id === fallbackId);

  async function saveEdit() {
    if (!edit?.routing_editable) return;
    setError(null);
    try {
      await updateAIFeatureRoute(edit.feature_key, {
        enabled,
        primary_provider_id: primaryId || null,
        primary_model: formValueToRouteModel(primaryModel),
        fallback_provider_id: fallbackId || null,
        fallback_model: formValueToRouteModel(fallbackModel),
        template_fallback_enabled: templateFb,
      });
      setEdit(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    }
  }

  return (
    <DashboardShell tone="soft" eyebrow="Admin" title="AI" description="">
      <div className="space-y-6">
        <AIControlCenterHeader
          title="Feature routing"
          description="Product status reflects implementation readiness. Operational status reflects routing and provider health."
        />
        <AIControlCenterNav />

        <Alert tone="info" title="Feature status documentation">
          See{" "}
          <code className="text-xs font-semibold">{DOCS_AUDIT_PATH}</code> in the
          repository for the full audit of Future vs Active features.
        </Alert>

        {loading ? <SkeletonLoader lines={6} /> : null}
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        {SECTIONS.map((sec) => (
          <section key={sec.id} className="space-y-2">
            <div>
              <h2 className="text-lg font-extrabold">{sec.title}</h2>
              {sec.description ? (
                <p className="text-sm text-muted-foreground">{sec.description}</p>
              ) : null}
            </div>
            <FeatureTable
              rows={sectionRows[sec.id] ?? []}
              onEdit={openEdit}
              onDetails={setDetails}
            />
          </section>
        ))}
      </div>

      <Drawer
        open={details !== null}
        onClose={() => setDetails(null)}
        title={details ? details.label : "Feature details"}
        description={details?.feature_key}
        footer={
          details ? (
            <Button variant="secondary" onClick={() => setDetails(null)}>
              Close
            </Button>
          ) : null
        }
      >
        {details ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {productBadge(details)}
              {operationalBadge(details)}
            </div>

            {details.future && details.future_helper_text ? (
              <Alert tone="info" title="Future feature">
                {details.future_helper_text}
              </Alert>
            ) : null}

            {details.safety_review_required && details.safety_note ? (
              <Alert tone="warning" title="Safety review">
                {details.safety_note}
              </Alert>
            ) : null}

            <div>
              <h3 className="mb-2 font-extrabold">Implementation readiness</h3>
              <ReadinessChecklist readiness={details.readiness} />
            </div>

            <p className="text-xs text-muted-foreground">
              Reference:{" "}
              <code className="font-semibold">
                {details.docs_reference || DOCS_AUDIT_PATH}
              </code>
            </p>

            {details.routing_editable ? (
              <Link href={`/admin/ai/usage?feature=${encodeURIComponent(details.feature_key)}`}>
                <Button variant="ghost" size="sm">
                  View usage
                </Button>
              </Link>
            ) : (
              <p className="text-sm text-muted-foreground">
                Routing and enable toggles are locked until this feature is implemented
                in product code.
              </p>
            )}
          </div>
        ) : null}
      </Drawer>

      <Modal
        open={!!edit}
        onClose={() => setEdit(null)}
        title={edit ? `Route: ${edit.label}` : "Edit routing"}
      >
        {edit && edit.routing_editable ? (
          <div className="space-y-3">
            <Switch checked={enabled} onCheckedChange={setEnabled} label="Feature enabled" />
            <Select
              label="Primary provider"
              value={primaryId}
              onChange={(e) => {
                setPrimaryId(e.target.value);
                setPrimaryModel(AUTO_MODEL);
              }}
            >
              <option value="">—</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display_name}
                </option>
              ))}
            </Select>
            <Select
              label="Primary model"
              value={primaryModel}
              onChange={(e) => setPrimaryModel(e.target.value)}
            >
              {modelOptionsForProvider(primaryProvider).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
            <Select
              label="Fallback provider"
              value={fallbackId}
              onChange={(e) => {
                setFallbackId(e.target.value);
                setFallbackModel(AUTO_MODEL);
              }}
            >
              <option value="">—</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display_name}
                </option>
              ))}
            </Select>
            <Select
              label="Fallback model"
              value={fallbackModel}
              onChange={(e) => setFallbackModel(e.target.value)}
            >
              {modelOptionsForProvider(fallbackProvider).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
            <Switch
              checked={templateFb}
              onCheckedChange={setTemplateFb}
              label="Allow template fallback"
            />
            <div className="flex gap-2">
              <Button onClick={() => void saveEdit()}>Save routing</Button>
              <Link href={`/admin/ai/usage?feature=${encodeURIComponent(edit.feature_key)}`}>
                <Button variant="ghost" size="sm">
                  View usage
                </Button>
              </Link>
            </div>
          </div>
        ) : null}
      </Modal>
    </DashboardShell>
  );
}
