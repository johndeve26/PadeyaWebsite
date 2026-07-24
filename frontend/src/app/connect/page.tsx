"use client";

import Link from "next/link";

import { ConnectHome } from "@/components/fan-connect/ConnectHome";
import { ConnectShell } from "@/components/fan-connect/ConnectShell";
import { Button } from "@/components/ui";

export default function ConnectHomePage() {
  return (
    <ConnectShell
      hideHeader
      title="Connect"
      description="Meet Explorers going where you’re going."
      actions={
        <Link href="/connect/settings">
          <Button variant="secondary">Settings</Button>
        </Link>
      }
    >
      <ConnectHome />
    </ConnectShell>
  );
}
