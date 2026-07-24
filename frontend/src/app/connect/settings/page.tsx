"use client";

import { ConnectSettingsForm } from "@/components/fan-connect/ConnectSettingsForm";
import { ConnectShell } from "@/components/fan-connect/ConnectShell";

export default function ConnectSettingsPage() {
  return (
    <ConnectShell
      title="Privacy & settings"
      description="On by default so you can connect — untick anytime. Directory listing is separate and never turns Connect on by itself."
    >
      <ConnectSettingsForm />
    </ConnectShell>
  );
}
