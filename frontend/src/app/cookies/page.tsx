import type { Metadata } from "next";

import { LegalDocument } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import { CookiesContent, COOKIES_TOC } from "@/lib/legal/cookies-content";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Cookie Policy",
  description: `How ${brand.name} uses cookies, localStorage, sessionStorage, ambassador referrals, preferences, analytics, and third-party payment storage.`,
  path: "/cookies",
});

export const revalidate = 3600;

export default function CookiesPage() {
  return (
    <LegalDocument
      title="Cookie Policy"
      description={`Cookies, localStorage, and sessionStorage that help ${brand.name} stay signed-in, secure, and useful.`}
      toc={COOKIES_TOC}
    >
      <CookiesContent />
    </LegalDocument>
  );
}
