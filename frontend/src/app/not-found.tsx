import type { Metadata } from "next";

import { NotFoundExperience } from "@/components/not-found/NotFoundExperience";

export const metadata: Metadata = {
  title: "Page not found",
  description:
    "The page you’re looking for may have moved, expired, or no longer exists.",
  robots: {
    index: false,
    follow: false,
    googleBot: { index: false, follow: false },
  },
};

/** Global App Router 404 — Next.js returns HTTP 404 for this route. */
export default function NotFound() {
  return <NotFoundExperience />;
}
