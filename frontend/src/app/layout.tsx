import type { Metadata, Viewport } from "next";
import { Manrope } from "next/font/google";

import { AuthProvider } from "@/components/auth/AuthProvider";
import { ImpersonationBanner } from "@/components/auth/ImpersonationBanner";
import { AnalyticsProvider } from "@/components/analytics/AnalyticsProvider";
import { MobileBottomNav } from "@/components/layout/MobileBottomNav";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { MaintenanceBanner } from "@/components/maintenance/MaintenanceBanner";
import { MaintenanceGate } from "@/components/maintenance/MaintenanceGate";
import { PwaProvider } from "@/components/pwa/PwaProvider";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { ThemeScript } from "@/components/theme/ThemeScript";
import { NotificationToastProvider } from "@/components/notifications/NotificationToastProvider";
import { brand } from "@/lib/brand";
import { JsonLdScript } from "@/lib/seo/jsonld";
import { siteGraphJsonLd } from "@/lib/seo/site-graph";
import { rootSeoMetadataFields } from "@/lib/seo/site";
import { THEME_COLOR } from "@/lib/theme";
import "@/styles/globals.css";

/**
 * Variable Manrope (single WOFF2) covers used weights:
 * medium(500), semibold(600), bold(700), extrabold(800), rare black(900).
 * Static multi-weight files were heavier with no design benefit.
 */
const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  display: "swap",
});

const seoRoot = rootSeoMetadataFields();

export const metadata: Metadata = {
  metadataBase: seoRoot.metadataBase,
  robots: seoRoot.robots,
  ...(seoRoot.verification ? { verification: seoRoot.verification } : {}),
  title: {
    default: brand.name,
    template: `%s · ${brand.name}`,
  },
  description: brand.tagline,
  applicationName: brand.name,
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    /** Prefer default so light theme keeps readable status text; theme-color drives Android chrome. */
    statusBarStyle: "default",
    title: brand.name,
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: THEME_COLOR.light },
    { media: "(prefers-color-scheme: dark)", color: THEME_COLOR.dark },
  ],
  colorScheme: "light dark",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <ThemeScript />
        <JsonLdScript data={siteGraphJsonLd()} />
      </head>
      <body
        className="flex min-h-full flex-col bg-background font-sans text-foreground"
        suppressHydrationWarning
      >
        <ThemeProvider>
          <AuthProvider>
            <AnalyticsProvider>
              <PwaProvider>
                <NotificationToastProvider>
                  <MaintenanceGate>
                    <ImpersonationBanner />
                    <MaintenanceBanner />
                    <SiteHeader />
                    <div className="min-w-0 flex-1">{children}</div>
                    <SiteFooter />
                    <MobileBottomNav />
                  </MaintenanceGate>
                </NotificationToastProvider>
              </PwaProvider>
            </AnalyticsProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
