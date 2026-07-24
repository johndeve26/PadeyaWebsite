import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Guest ticket claim · Pàdéyá",
  description:
    "Claim tickets from guest checkout, or sign in to access tickets already on your Pàdéyá account.",
  robots: { index: false, follow: false },
};

export default function CheckoutClaimLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
