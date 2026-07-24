"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  Select,
  Switch,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  disableEmailProviderSettings,
  fetchEmailProviderSettings,
  sendEmailSettingsTest,
  updateEmailProviderSettings,
  type EmailProviderSettings,
} from "@/lib/email-api";
import { formatDateTime } from "@/lib/format";

type SecurityMode = "tls" | "ssl" | "none";

export default function AdminEmailSettingsPage() {
  const [settings, setSettings] = useState<EmailProviderSettings | null>(null);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [provider, setProvider] = useState("log");
  const [devMode, setDevMode] = useState(false);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [security, setSecurity] = useState<SecurityMode>("tls");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [fromEmail, setFromEmail] = useState("");
  const [fromName, setFromName] = useState("Pàdéyá");
  const [replyTo, setReplyTo] = useState("");
  const [testTo, setTestTo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [disabling, setDisabling] = useState(false);

  const smtpMissing = useMemo(() => {
    if (provider !== "smtp" || devMode) return false;
    return !smtpHost.trim() || !fromEmail.trim();
  }, [provider, devMode, smtpHost, fromEmail]);

  const applySettings = useCallback((data: EmailProviderSettings) => {
    setSettings(data);
    setEmailEnabled(data.email_enabled);
    setProvider(data.provider || "log");
    setDevMode(data.dev_mode);
    setSmtpHost(data.smtp_host || "");
    setSmtpPort(String(data.smtp_port || (data.smtp_use_ssl ? 465 : 587)));
    if (data.smtp_use_ssl) setSecurity("ssl");
    else if (data.smtp_use_tls) setSecurity("tls");
    else setSecurity("none");
    setFromEmail(data.smtp_from_email || "");
    setFromName(data.smtp_from_name || "Pàdéyá");
    setReplyTo(data.smtp_reply_to || "");
    setSmtpUsername("");
    setSmtpPassword("");
  }, []);

  const load = useCallback(async () => {
    const data = await fetchEmailProviderSettings();
    applySettings(data);
  }, [applySettings]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Failed to load email settings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      const port = Number(smtpPort);
      if (!Number.isFinite(port) || port < 1 || port > 65535) {
        throw new Error("SMTP port must be between 1 and 65535");
      }
      const data = await updateEmailProviderSettings({
        email_enabled: emailEnabled,
        provider,
        dev_mode: devMode,
        smtp_host: smtpHost.trim() || null,
        smtp_port: port,
        smtp_use_tls: security === "tls",
        smtp_use_ssl: security === "ssl",
        smtp_from_email: fromEmail.trim() || null,
        smtp_from_name: fromName.trim() || "Pàdéyá",
        smtp_reply_to: replyTo.trim() || null,
        smtp_username: smtpUsername.trim() || null,
        smtp_password: smtpPassword.trim() || null,
      });
      applySettings(data);
      setNote(
        "Email settings saved. The outbox worker uses these values on the next batch — no rebuild required.",
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Could not save email settings",
      );
    } finally {
      setSaving(false);
    }
  }

  async function onTest() {
    setTesting(true);
    setError(null);
    setNote(null);
    try {
      const result = await sendEmailSettingsTest(testTo.trim() || undefined);
      if (result.ok) {
        const recipient = (result.to || testTo.trim() || "").trim();
        if (result.skipped) {
          setNote(
            `Test skipped (${result.provider ?? "disabled"}). Email sending may be turned off.`,
          );
        } else if (recipient && result.delivered_to_inbox === false) {
          setNote(
            `Log only — nothing was delivered to ${recipient}. The message was recorded in the app (backend logs and Admin → Emails). To receive real mail: set Provider to SMTP, fill SMTP settings, turn off Dev / log mode, Save, then send again.`,
          );
        } else if (recipient) {
          setNote(
            `Test email sent via ${result.provider ?? "smtp"} to ${recipient}. Check inbox and spam.`,
          );
        } else {
          setNote(
            `SMTP connection OK${result.smtp_host ? ` (${result.smtp_host}:${result.smtp_port})` : ""}.`,
          );
        }
      } else {
        setError(result.error || "Email test failed");
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Email test failed");
    } finally {
      setTesting(false);
    }
  }

  async function onDisable() {
    setDisabling(true);
    setError(null);
    setNote(null);
    try {
      const data = await disableEmailProviderSettings();
      applySettings(data);
      setNote("Email sending disabled. Pending messages will be skipped until re-enabled.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not disable email sending",
      );
    } finally {
      setDisabling(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Email settings"
      description="Manage Pàdéyá transactional email providers and SMTP credentials. Secrets are encrypted and never shown in full."
      actions={
        <Link href="/admin/emails">
          <Button variant="secondary" size="sm">
            Outbox
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
        <Alert tone="success" title="Status">
          {note}
        </Alert>
      ) : null}
      {smtpMissing ? (
        <Alert tone="warning" title="SMTP incomplete">
          Provider is SMTP but host or from email is missing. Save complete settings
          before expecting delivery.
        </Alert>
      ) : null}

      {settings ? (
        <Card className="mb-4 space-y-2 p-4">
          <h2 className="text-sm font-semibold text-foreground">Current status</h2>
          <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
            <Badge tone="neutral" size="sm">
              {settings.provider}
            </Badge>
            <span>{settings.email_enabled ? "Sending on" : "Sending off"}</span>
            <span>
              Pending: {settings.pending_emails_count} · Failed:{" "}
              {settings.failed_emails_count}
            </span>
            {settings.last_successful_send_at ? (
              <span>
                Last successful send: {formatDateTime(settings.last_successful_send_at)}
              </span>
            ) : (
              <span>No successful send recorded</span>
            )}
            {settings.last_test_at ? (
              <span>
                Last test: {formatDateTime(settings.last_test_at)} ·{" "}
                {settings.last_test_status || "—"}
                {settings.last_test_error ? ` — ${settings.last_test_error}` : ""}
              </span>
            ) : null}
            {settings.smtp_password_configured ? (
              <span>Password: {settings.smtp_password_hint || "configured"}</span>
            ) : (
              <span>Password: not configured</span>
            )}
            {settings.smtp_username_masked ? (
              <span>Username: {settings.smtp_username_masked}</span>
            ) : null}
          </div>
        </Card>
      ) : null}

      <Card className="p-5">
        <form className="space-y-5" onSubmit={onSave}>
          <section className="space-y-4">
            <h2 className="text-sm font-semibold text-foreground">Email mode</h2>
            <Switch
              id="email-enabled"
              checked={emailEnabled}
              onCheckedChange={setEmailEnabled}
              label="Email sending enabled"
              description="When off, pending emails are skipped."
            />
            <Switch
              id="email-dev-mode"
              checked={devMode}
              onCheckedChange={setDevMode}
              label="Dev / log mode"
              description="When on, messages are logged only — SMTP is never used."
            />
            <Select
              label="Provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="log">Log only</option>
              <option value="smtp">SMTP</option>
              <option value="postmark">Postmark (placeholder)</option>
              <option value="brevo">Brevo (placeholder)</option>
              <option value="resend">Resend (placeholder)</option>
              <option value="sendgrid">SendGrid (placeholder)</option>
            </Select>
          </section>

          <section className="space-y-4 border-t border-border pt-5">
            <h2 className="text-sm font-semibold text-foreground">SMTP configuration</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="SMTP host"
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                placeholder="smtp.example.com"
              />
              <Input
                label="SMTP port"
                value={smtpPort}
                onChange={(e) => setSmtpPort(e.target.value)}
                inputMode="numeric"
              />
              <Select
                label="Security"
                value={security}
                onChange={(e) => setSecurity(e.target.value as SecurityMode)}
              >
                <option value="tls">STARTTLS</option>
                <option value="ssl">SSL</option>
                <option value="none">None</option>
              </Select>
              <Input
                label="SMTP username"
                value={smtpUsername}
                onChange={(e) => setSmtpUsername(e.target.value)}
                autoComplete="off"
                hint={
                  settings?.smtp_username_masked
                    ? `Configured as ${settings.smtp_username_masked}. Leave blank to keep.`
                    : "Optional for some relays"
                }
              />
              <Input
                label="SMTP password"
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                autoComplete="new-password"
                hint={
                  settings?.smtp_password_configured
                    ? "Configured — leave blank to keep existing password"
                    : "Required for authenticated SMTP"
                }
              />
              <Input
                label="From email"
                type="email"
                value={fromEmail}
                onChange={(e) => setFromEmail(e.target.value)}
                hint="Must be an address your SMTP server allows (often the same as SMTP username). @padeya.com needs domain verification with your provider."
              />
              <Input
                label="From name"
                value={fromName}
                onChange={(e) => setFromName(e.target.value)}
                hint="Use Pàdéyá for brand consistency"
              />
              <Input
                label="Reply-to email"
                type="email"
                value={replyTo}
                onChange={(e) => setReplyTo(e.target.value)}
              />
            </div>
          </section>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save settings"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={disabling || saving}
              onClick={() => void onDisable()}
            >
              {disabling ? "Disabling…" : "Disable email sending"}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="mt-4 space-y-3 p-5">
        <h2 className="text-sm font-semibold text-foreground">Test email</h2>
        <p className="text-sm text-muted-foreground">
          Leave recipient empty to test SMTP login only. Save settings first if you
          changed the form. With Provider &quot;Log only&quot; or Dev / log mode on,
          tests never reach your inbox — only SMTP with dev mode off delivers mail.
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-[220px] flex-1">
            <Input
              label="Test recipient email"
              type="email"
              value={testTo}
              onChange={(e) => setTestTo(e.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <Button
            type="button"
            variant="secondary"
            disabled={testing}
            onClick={() => void onTest()}
          >
            {testing ? "Testing…" : "Send test email"}
          </Button>
        </div>
      </Card>
    </DashboardShell>
  );
}
