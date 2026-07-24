"use client";

import { useCallback, useEffect, useState } from "react";

import {
  AIControlCenterHeader,
  AIControlCenterNav,
} from "@/components/admin/ai/AIControlCenterNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  Modal,
  Select,
  SkeletonLoader,
  Switch,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createAIProviderProfile,
  deleteAIProviderProfile,
  fetchAIProviderProfiles,
  testAIProviderProfile,
  updateAIProviderProfile,
} from "@/lib/ai-api";
import type { AIProviderProfile } from "@/lib/types/ai";

function healthTone(status: string) {
  if (status === "healthy") return "accent" as const;
  if (status === "needs_configuration") return "warning" as const;
  if (status === "failing") return "danger" as const;
  return "outline" as const;
}

function modelsToText(models: string[] | undefined): string {
  return (models ?? []).join(", ");
}

function parseModels(text: string): string[] {
  return text
    .split(/[,;\n]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function AdminAIProvidersPage() {
  const [providers, setProviders] = useState<AIProviderProfile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<AIProviderProfile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AIProviderProfile | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [formType, setFormType] = useState("openai");
  const [formName, setFormName] = useState("");
  const [formModel, setFormModel] = useState("gpt-4o-mini");
  const [formEnvKey, setFormEnvKey] = useState(false);
  const [formApiKey, setFormApiKey] = useState("");

  const [editName, setEditName] = useState("");
  const [editBaseUrl, setEditBaseUrl] = useState("");
  const [editModel, setEditModel] = useState("");
  const [editModels, setEditModels] = useState("");
  const [editPriority, setEditPriority] = useState("100");
  const [editTimeout, setEditTimeout] = useState("30");
  const [editMaxTokens, setEditMaxTokens] = useState("800");
  const [editEnvKey, setEditEnvKey] = useState(false);
  const [editNotes, setEditNotes] = useState("");
  const [editApiKey, setEditApiKey] = useState("");
  const [clearStoredKey, setClearStoredKey] = useState(false);

  const load = useCallback(async () => {
    setProviders(await fetchAIProviderProfiles());
  }, []);

  useEffect(() => {
    void load()
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load providers"),
      )
      .finally(() => setLoading(false));
  }, [load]);

  function openEdit(p: AIProviderProfile) {
    setEditTarget(p);
    setEditName(p.display_name);
    setEditBaseUrl(p.base_url ?? "");
    setEditModel(p.default_model ?? "");
    setEditModels(modelsToText(p.available_models));
    setEditPriority(String(p.priority));
    setEditTimeout(String(p.timeout_seconds));
    setEditMaxTokens(String(p.max_tokens_default));
    setEditEnvKey(p.use_env_api_key);
    setEditNotes(p.notes ?? "");
    setEditApiKey("");
    setClearStoredKey(false);
  }

  async function onCreate() {
    setError(null);
    try {
      await createAIProviderProfile({
        provider_type: formType,
        display_name: formName.trim() || `${formType} provider`,
        default_model: formModel,
        available_models: formModel.trim()
          ? [formModel.trim()]
          : undefined,
        use_env_api_key: formEnvKey && !formApiKey.trim(),
        ...(formApiKey.trim() ? { api_key: formApiKey.trim() } : {}),
      });
      setAddOpen(false);
      setFormApiKey("");
      setNote("Provider added.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    }
  }

  async function onSaveEdit() {
    if (!editTarget) return;
    setError(null);
    setBusy(true);
    try {
      const models = parseModels(editModels);
      const defaultModel = editModel.trim() || models[0] || undefined;
      await updateAIProviderProfile(editTarget.id, {
        display_name: editName.trim() || editTarget.display_name,
        base_url: editBaseUrl.trim() || undefined,
        default_model: defaultModel,
        available_models: models.length ? models : defaultModel ? [defaultModel] : [],
        priority: Number.parseInt(editPriority, 10) || 100,
        timeout_seconds: Number.parseInt(editTimeout, 10) || 30,
        max_tokens_default: Number.parseInt(editMaxTokens, 10) || 800,
        use_env_api_key: editEnvKey,
        notes: editNotes.trim() || undefined,
        ...(clearStoredKey
          ? { clear_api_key: true }
          : editApiKey.trim()
            ? { api_key: editApiKey.trim() }
            : {}),
      });
      setEditTarget(null);
      setNote("Provider updated.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmDelete() {
    if (!deleteTarget) return;
    setError(null);
    setBusy(true);
    try {
      await deleteAIProviderProfile(deleteTarget.id);
      setDeleteTarget(null);
      setNote("Provider removed.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleEnabled(p: AIProviderProfile) {
    try {
      await updateAIProviderProfile(p.id, { is_enabled: !p.is_enabled });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function onTest(id: string) {
    setTestingId(id);
    setNote(null);
    try {
      const res = await testAIProviderProfile(id);
      setNote(String(res.message ?? "Test complete"));
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Test failed");
    } finally {
      setTestingId(null);
    }
  }

  const canDelete = (p: AIProviderProfile) => p.provider_type !== "template_fallback";

  return (
    <DashboardShell tone="soft" eyebrow="Admin" title="AI" description="">
      <div className="space-y-6">
        <AIControlCenterHeader
          title="Providers"
          description="Manage multiple provider profiles. Different features can route to different models."
        />
        <AIControlCenterNav />

        <Alert tone="info" title="API keys">
          Paste a provider API key on each profile to store it encrypted in the
          database (same Fernet key as Email SMTP:{" "}
          <code className="text-xs">EMAIL_SETTINGS_ENCRYPTION_KEY</code>), or enable
          “Use AI_API_KEY from environment” for a shared server key.
        </Alert>

        <div className="flex justify-end">
          <Button onClick={() => setAddOpen(true)}>Add provider</Button>
        </div>

        {loading ? <SkeletonLoader lines={4} /> : null}
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}
        {note ? (
          <Alert tone="success" title="Done">
            {note}
          </Alert>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {providers.map((p) => (
            <Card key={p.id} className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-extrabold">{p.display_name}</h3>
                  <p className="text-xs text-muted-foreground">{p.provider_type}</p>
                </div>
                <Badge tone={healthTone(p.health_status)}>{p.health_status}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                Model {p.default_model ?? "—"} · priority {p.priority}
              </p>
              <p className="text-xs text-muted-foreground truncate">{p.base_url}</p>
              <p className="text-xs">
                Key:{" "}
                {p.api_key_status.configured
                  ? p.api_key_status.masked ?? "configured"
                  : "not configured"}
                {p.use_env_api_key ? " (env)" : ""}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>
                  Edit
                </Button>
                {canDelete(p) ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setDeleteTarget(p)}
                  >
                    Delete
                  </Button>
                ) : null}
                <Switch
                  checked={p.is_enabled}
                  onCheckedChange={() => void toggleEnabled(p)}
                  label="Enabled"
                />
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={testingId === p.id}
                  onClick={() => void onTest(p.id)}
                >
                  {testingId === p.id ? "Testing…" : "Test"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Add provider">
        <div className="space-y-3">
          <Select
            label="Provider type"
            value={formType}
            onChange={(e) => setFormType(e.target.value)}
          >
            <option value="openai">OpenAI</option>
            <option value="openai_compatible">OpenAI-compatible</option>
            <option value="anthropic">Anthropic</option>
            <option value="gemini">Gemini</option>
            <option value="grok">Grok</option>
            <option value="template_fallback">Template fallback</option>
          </Select>
          <Input
            label="Display name"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
          />
          <Input
            label="Default model"
            value={formModel}
            onChange={(e) => setFormModel(e.target.value)}
          />
          <Switch
            checked={formEnvKey}
            onCheckedChange={setFormEnvKey}
            label="Use AI_API_KEY from environment (when no key pasted below)"
          />
          {formType !== "template_fallback" ? (
            <Input
              label="API key (optional, stored encrypted)"
              type="password"
              autoComplete="off"
              value={formApiKey}
              onChange={(e) => setFormApiKey(e.target.value)}
              hint="Leave empty to configure later. Pasting a key disables env-only mode."
            />
          ) : null}
          <Button onClick={() => void onCreate()}>Create</Button>
        </div>
      </Modal>

      <Modal
        open={editTarget !== null}
        onClose={() => setEditTarget(null)}
        title="Edit provider"
      >
        {editTarget ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Type: {editTarget.provider_type} (fixed at create)
            </p>
            <Input
              label="Display name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
            />
            {editTarget.provider_type !== "template_fallback" ? (
              <>
                <Input
                  label="Base URL"
                  value={editBaseUrl}
                  onChange={(e) => setEditBaseUrl(e.target.value)}
                />
                <Switch
                  checked={editEnvKey}
                  onCheckedChange={setEditEnvKey}
                  label="Use AI_API_KEY from environment (overrides stored key when set on server)"
                />
                <Input
                  label="API key"
                  type="password"
                  autoComplete="off"
                  value={editApiKey}
                  onChange={(e) => setEditApiKey(e.target.value)}
                  hint={
                    editTarget.api_key_status.configured
                      ? `Current: ${editTarget.api_key_status.masked ?? "configured"}. Paste a new key to rotate, or clear below.`
                      : "Paste key to store encrypted on this profile."
                  }
                />
                {editTarget.api_key_status.configured ? (
                  <Switch
                    checked={clearStoredKey}
                    onCheckedChange={setClearStoredKey}
                    label="Clear stored API key on save"
                  />
                ) : null}
              </>
            ) : null}
            <Input
              label="Default model"
              value={editModel}
              onChange={(e) => setEditModel(e.target.value)}
            />
            <Input
              label="Available models (comma-separated)"
              value={editModels}
              onChange={(e) => setEditModels(e.target.value)}
            />
            <div className="grid gap-3 sm:grid-cols-3">
              <Input
                label="Priority"
                value={editPriority}
                onChange={(e) => setEditPriority(e.target.value)}
              />
              <Input
                label="Timeout (s)"
                value={editTimeout}
                onChange={(e) => setEditTimeout(e.target.value)}
              />
              <Input
                label="Max tokens default"
                value={editMaxTokens}
                onChange={(e) => setEditMaxTokens(e.target.value)}
              />
            </div>
            <Input
              label="Notes"
              value={editNotes}
              onChange={(e) => setEditNotes(e.target.value)}
            />
            <div className="flex gap-2">
              <Button disabled={busy} onClick={() => void onSaveEdit()}>
                Save changes
              </Button>
              <Button variant="secondary" onClick={() => setEditTarget(null)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete provider"
      >
        {deleteTarget ? (
          <div className="space-y-4">
            <p className="text-sm">
              Remove <strong>{deleteTarget.display_name}</strong>? This cannot be undone.
              If any feature routes still use this provider, delete will be blocked until
              you reassign them on Feature routing.
            </p>
            <div className="flex gap-2">
              <Button disabled={busy} onClick={() => void onConfirmDelete()}>
                Delete provider
              </Button>
              <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </DashboardShell>
  );
}
