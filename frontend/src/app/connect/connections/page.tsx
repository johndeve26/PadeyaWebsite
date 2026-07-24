"use client";

import { ConnectShell } from "@/components/fan-connect/ConnectShell";
import { ConnectionsList } from "@/components/fan-connect/ConnectionsList";

export default function ConnectConnectionsPage() {
  return (
    <ConnectShell
      title="Connections"
      description="Accepted Fan Connect pairs. Message stays on Pàdéyá."
    >
      <ConnectionsList />
    </ConnectShell>
  );
}
