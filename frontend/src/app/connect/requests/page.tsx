"use client";

import { useState } from "react";

import { ConnectRequestList } from "@/components/fan-connect/ConnectRequestList";
import { ConnectShell } from "@/components/fan-connect/ConnectShell";
import { Button } from "@/components/ui";

export default function ConnectRequestsPage() {
  const [box, setBox] = useState<"incoming" | "outgoing">("incoming");

  return (
    <ConnectShell
      title="Requests"
      description="Accept to unlock in-app messaging. Decline or cancel anytime."
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={box === "incoming" ? "primary" : "secondary"}
          onClick={() => setBox("incoming")}
        >
          Incoming
        </Button>
        <Button
          size="sm"
          variant={box === "outgoing" ? "primary" : "secondary"}
          onClick={() => setBox("outgoing")}
        >
          Outgoing
        </Button>
      </div>
      <ConnectRequestList box={box} />
    </ConnectShell>
  );
}
