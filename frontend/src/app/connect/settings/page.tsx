"use client";

import { ConnectSettingsForm } from "@/components/fan-connect/ConnectSettingsForm";
import { ConnectShell } from "@/components/fan-connect/ConnectShell";

export default function ConnectSettingsPage() {
  return (
    <ConnectShell
      title="Privacy & settings"
      description="Private by default — Fan Connect stays off until you enable it. Directory membership never turns this on by itself."
    >
      <ConnectSettingsForm />
    </ConnectShell>
  );
}
