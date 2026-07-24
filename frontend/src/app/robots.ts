import type { MetadataRoute } from "next";

import { siteOrigin } from "@/lib/seo/site";

export default function robots(): MetadataRoute.Robots {
  const origin = siteOrigin();
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/host/",
          "/dashboard/",
          "/admin/",
          "/support/desk",
          "/support/cases",
          "/support/refunds",
          "/ambassador/",
          "/staff/",
          "/api/",
          "/login",
          "/register",
        ],
      },
    ],
    sitemap: `${origin}/sitemap.xml`,
  };
}
