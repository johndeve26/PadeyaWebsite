"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, Input, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  estimateResolvedRecipientCount,
  MAX_ADMIN_TEST_RECIPIENTS,
  parseRecipientEmailsInput,
  type RecipientMode,
} from "@/lib/admin-email-recipients";
import { userHasPermission } from "@/lib/auth/permissions";
import {
  fetchAdminEmailTemplate,
  previewAdminEmailTemplate,
  restoreAdminEmailTemplate,
  testSendAdminEmailTemplate,
  updateAdminEmailTemplate,
  type AdminEmailTemplate,
} from "@/lib/email-api";

const RECIPIENT_GROUPS = [
  "super_admin",
  "support",
  "moderation",
  "finance",
  "operations",
  "marketing",
  "custom",
];

const RECIPIENT_MODES: { id: RecipientMode; label: string }[] = [
  { id: "group", label: "Admin group" },
  { id: "custom", label: "Custom emails" },
  { id: "group_and_custom", label: "Admin group + custom emails" },
];

const DELIVERY_MODES = ["instant", "disabled", "digest"];

export default function AdminEmailTemplateEditPage() {
  const params = useParams();
  const templateKey = decodeURIComponent(String(params.templateKey ?? ""));
  const { user } = useAuth();
  const canManageRecipients = userHasPermission(
    user,
    "admin.emails.manage_recipients",
    "admin.full_access",
  );

  const [tpl, setTpl] = useState<AdminEmailTemplate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ subject: string; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const [subject, setSubject] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [textBody, setTextBody] = useState("");
  const [htmlBody, setHtmlBody] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [recipientMode, setRecipientMode] = useState<RecipientMode>("group");
  const [recipientGroup, setRecipientGroup] = useState("operations");
  const [deliveryMode, setDeliveryMode] = useState("instant");
  const [customEmails, setCustomEmails] = useState("");
  const [threshold, setThreshold] = useState("");
  const [testEmails, setTestEmails] = useState("");

  const customParse = useMemo(
    () => parseRecipientEmailsInput(customEmails),
    [customEmails],
  );

  const testParse = useMemo(
    () => parseRecipientEmailsInput(testEmails, MAX_ADMIN_TEST_RECIPIENTS),
    [testEmails],
  );

  const recipientPreviewCount = useMemo(() => {
    if (!tpl) return 0;
    if (customParse.error && recipientMode !== "group") {
      return 0;
    }
    return estimateResolvedRecipientCount({
      mode: recipientMode,
      customEmails: customParse.error ? [] : customParse.emails,
      serverResolvedCount: tpl.resolved_recipient_count,
      savedCustomCount: tpl.custom_recipient_emails?.length ?? 0,
    });
  }, [tpl, recipientMode, customParse]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchAdminEmailTemplate(templateKey);
        if (!active) return;
        setTpl(row);
        setSubject(row.subject);
        setPreviewText(row.preview_text);
        setTextBody(row.text_body ?? "");
        setHtmlBody(row.html_body ?? "");
        setEnabled(row.is_enabled);
        setRecipientMode(row.recipient_mode ?? "group");
        setRecipientGroup(row.recipient_group);
        setDeliveryMode(row.delivery_mode);
        setCustomEmails(
          row.recipient_emails_display ??
            (row.custom_recipient_emails ?? []).join(", "),
        );
        setThreshold(row.threshold_amount != null ? String(row.threshold_amount) : "");
        setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load template");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [templateKey]);

  async function save() {
    if (!tpl) return;
    if (canManageRecipients && recipientMode !== "group" && customParse.error) {
      setError(customParse.error);
      return;
    }
    setBusy(true);
    setNote(null);
    setError(null);
    try {
      const patch: Parameters<typeof updateAdminEmailTemplate>[1] = {
        subject,
        preview_text: previewText,
        text_body: textBody || undefined,
        html_body: htmlBody || undefined,
        is_enabled: enabled,
        delivery_mode: deliveryMode,
        threshold_amount: threshold.trim() ? Number(threshold) : null,
      };
      if (canManageRecipients) {
        patch.recipient_mode = recipientMode;
        patch.recipient_group = recipientGroup;
        if (recipientMode !== "group") {
          patch.recipient_emails = customEmails.trim();
        } else {
          patch.recipient_emails = "";
        }
      }
      const updated = await updateAdminEmailTemplate(templateKey, patch);
      setTpl(updated);
      setCustomEmails(
        updated.recipient_emails_display ??
          (updated.custom_recipient_emails ?? []).join(", "),
      );
      setNote("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onPreview() {
    setBusy(true);
    try {
      const row = await previewAdminEmailTemplate(templateKey);
      setPreview({ subject: row.subject, text: row.text });
      setNote("Preview generated with sample variables.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  async function onTestSend() {
    if (testEmails.trim() && testParse.error) {
      setError(testParse.error);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await testSendAdminEmailTemplate(templateKey, {
        test_recipient_emails: testEmails.trim() || undefined,
      });
      setNote(
        `Test email queued to ${result.recipient_count} recipient${result.recipient_count === 1 ? "" : "s"}.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Test send failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRestore() {
    setBusy(true);
    try {
      const row = await restoreAdminEmailTemplate(templateKey);
      setTpl(row);
      setSubject(row.subject);
      setPreviewText(row.preview_text);
      setTextBody("");
      setHtmlBody("");
      setEnabled(row.is_enabled);
      setRecipientMode(row.recipient_mode ?? "group");
      setRecipientGroup(row.recipient_group);
      setDeliveryMode(row.delivery_mode);
      setCustomEmails(
        row.recipient_emails_display ??
          (row.custom_recipient_emails ?? []).join(", "),
      );
      setThreshold(row.threshold_amount != null ? String(row.threshold_amount) : "");
      setNote("Restored registry defaults.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Restore failed");
    } finally {
      setBusy(false);
    }
  }

  const showGroup = recipientMode === "group" || recipientMode === "group_and_custom";
  const showCustom = recipientMode === "custom" || recipientMode === "group_and_custom";
  const saveBlocked =
    canManageRecipients && showCustom && Boolean(customParse.error && customEmails.trim());

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title={tpl?.title ?? templateKey}
      description="Edit admin-only platform notification copy. Use {{variable}} placeholders from the list below."
      actions={
        <Link href="/admin/emails/templates">
          <Button size="sm" variant="secondary">
            All templates
          </Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="OK">
          {note}
        </Alert>
      ) : null}

      {tpl ? (
        <div className="grid gap-6 lg:grid-cols-[1fr,minmax(0,22rem)]">
          <Card padded className="space-y-4">
            <Input label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
            <Input
              label="Preview text"
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
            />
            <Textarea
              label="Plain text body (optional override)"
              hint="Leave empty to use the default registry layout."
              rows={6}
              value={textBody}
              onChange={(e) => setTextBody(e.target.value)}
            />
            <Textarea
              label="HTML body (optional override)"
              rows={8}
              value={htmlBody}
              onChange={(e) => setHtmlBody(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                checked={enabled}
                disabled={tpl.is_required}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              Enabled
              {tpl.is_required ? (
                <span className="text-xs font-normal text-muted-foreground">(required template)</span>
              ) : null}
            </label>

            <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
              <p className="text-sm font-extrabold text-foreground">Recipients</p>
              {!canManageRecipients ? (
                <p className="text-xs text-muted-foreground">
                  You can view recipient settings but need{" "}
                  <span className="font-mono">admin.emails.manage_recipients</span> to edit them.
                </p>
              ) : null}

              <label className="block text-sm">
                <span className="mb-1 block font-semibold">Recipient mode</span>
                <select
                  className="h-10 w-full rounded-md border border-border bg-card px-2 text-sm disabled:opacity-60"
                  value={recipientMode}
                  disabled={!canManageRecipients}
                  onChange={(e) => setRecipientMode(e.target.value as RecipientMode)}
                >
                  {RECIPIENT_MODES.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </label>

              {showGroup ? (
                <label className="block text-sm">
                  <span className="mb-1 block font-semibold">Admin group</span>
                  <select
                    className="h-10 w-full rounded-md border border-border bg-card px-2 text-sm disabled:opacity-60"
                    value={recipientGroup}
                    disabled={!canManageRecipients}
                    onChange={(e) => setRecipientGroup(e.target.value)}
                  >
                    {RECIPIENT_GROUPS.filter((g) => g !== "custom").map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              {showCustom ? (
                <Input
                  label="Recipient emails"
                  hint="Separate multiple emails with commas."
                  placeholder="admin@padeya.com, support@padeya.com, finance@padeya.com"
                  value={customEmails}
                  disabled={!canManageRecipients}
                  onChange={(e) => setCustomEmails(e.target.value)}
                />
              ) : null}

              {customParse.error && showCustom && customEmails.trim() ? (
                <p className="text-sm font-semibold text-destructive">{customParse.error}</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {recipientPreviewCount} recipient{recipientPreviewCount === 1 ? "" : "s"}
                  {recipientMode === "group_and_custom" && !customParse.error
                    ? " (estimate until saved)"
                    : null}
                </p>
              )}
            </div>

            <label className="block text-sm">
              <span className="mb-1 block font-semibold">Delivery</span>
              <select
                className="h-10 w-full rounded-md border border-border bg-card px-2 text-sm"
                value={deliveryMode}
                onChange={(e) => setDeliveryMode(e.target.value)}
              >
                {DELIVERY_MODES.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <Input
              label="High-value threshold (amount)"
              hint="For large-order templates — instant send only when amount ≥ threshold."
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />

            <Input
              label="Test send recipients"
              hint={`Optional comma-separated addresses (max ${MAX_ADMIN_TEST_RECIPIENTS}). Leave empty to send to your admin email.`}
              placeholder="admin@padeya.com, support@padeya.com"
              value={testEmails}
              onChange={(e) => setTestEmails(e.target.value)}
            />
            {testEmails.trim() && testParse.error ? (
              <p className="text-sm font-semibold text-destructive">{testParse.error}</p>
            ) : testEmails.trim() && !testParse.error ? (
              <p className="text-sm text-muted-foreground">
                {testParse.emails.length} test recipient
                {testParse.emails.length === 1 ? "" : "s"}
              </p>
            ) : null}

            <div className="flex flex-wrap gap-2 pt-2">
              <Button disabled={busy || saveBlocked} onClick={() => void save()}>
                Save
              </Button>
              <Button disabled={busy} variant="secondary" onClick={() => void onPreview()}>
                Preview
              </Button>
              <Button
                disabled={busy || Boolean(testEmails.trim() && testParse.error)}
                variant="secondary"
                onClick={() => void onTestSend()}
              >
                Test send
              </Button>
              <Button disabled={busy} variant="ghost" onClick={() => void onRestore()}>
                Restore default
              </Button>
            </div>
          </Card>

          <div className="space-y-4">
            <Card padded className="space-y-2">
              <p className="text-sm font-extrabold text-foreground">Variables</p>
              <ul className="font-mono text-xs text-muted-foreground">
                {tpl.variables.map((v) => (
                  <li key={v}>{`{{${v}}}`}</li>
                ))}
              </ul>
            </Card>
            {preview ? (
              <Card padded className="space-y-2">
                <p className="text-sm font-extrabold">{preview.subject}</p>
                <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">
                  {preview.text}
                </pre>
              </Card>
            ) : null}
          </div>
        </div>
      ) : null}
    </DashboardShell>
  );
}
