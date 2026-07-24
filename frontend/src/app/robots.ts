import type { MetadataRoute } from "next";

import {
  getCanonicalSiteOrigin,
  shouldIndexEnvironment,
} from "@/lib/seo/env-policy";

const PRODUCTION_DISALLOW = [
  "/admin/",
  "/dashboard/",
  "/host/",
  "/sponsor/",
  "/connect/",
  "/messages/",
  "/staff/",
  "/ambassador/",
  "/api/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/support/tickets/",
  "/support/desk",
  "/support/cases",
  "/support/refunds",
  "/events/*/checkout",
  "/merch/hosts/*/checkout",
  "/checkout/",
  "/tickets/claim",
  "/team/invite/",
  "/account/appeal",
  "/account/suspended",
  "/demo",
] as const;

export default function robots(): MetadataRoute.Robots {
  if (!shouldIndexEnvironment()) {
    return {
      rules: [
        {
          userAgent: "*",
          disallow: "/",
        },
      ],
      // Do not advertise a production sitemap from staging/preview/dev.
    };
  }

  const origin = getCanonicalSiteOrigin();
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [...PRODUCTION_DISALLOW],
      },
    ],
    sitemap: `${origin}/sitemap.xml`,
  };
}
