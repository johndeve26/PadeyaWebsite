import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Claim transferred ticket · Pàdéyá",
  description:
    "Accept a ticket someone transferred to you — log in with the recipient email from the message.",
  robots: { index: false, follow: false },
};

export default function TicketTransferClaimLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
