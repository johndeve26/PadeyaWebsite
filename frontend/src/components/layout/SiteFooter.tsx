"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useHeaderAccess } from "@/components/layout/HeaderWorkspaceButton";
import { Container, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";
import { cn } from "@/lib/cn";
import { SPONSORSHIP_MARKETPLACE_PATH } from "@/lib/sponsor-marketplace-paths";

import { isWorkspacePath } from "./workspacePath";

const discoverLinks = [
  { href: "/events", label: "Events" },
  { href: "/events/near-me", label: "Near me" },
  { href: "/hosts", label: "Hosts" },
  { href: "/fans", label: "Fans" },
  { href: SPONSORSHIP_MARKETPLACE_PATH, label: "Sponsors" },
  { href: "/merch", label: "Shop" },
];

const forFansLinks = [
  { href: "/for-fans", label: "For fans" },
  { href: "/dashboard/passport", label: "Fan Passport" },
  { href: "/connect", label: "Fan Connect" },
  { href: "/ambassadors", label: "Ambassadors" },
  { href: "/dashboard/tickets", label: "My tickets" },
  { href: "/dashboard/merchandise", label: "My merch" },
];

const forHostsLinks = [
  { href: "/for-hosts", label: "For hosts" },
  { href: "/hosts", label: "Host directory" },
  { href: "/host/onboarding", label: "Become a host" },
  { href: "/host/events/new", label: "Create event" },
  { href: "/host/merchandise", label: "Merch Studio" },
  { href: "/pricing", label: "Pricing" },
];

const resourcesLinks = [
  { href: "/blog", label: "Blog" },
  { href: "/help", label: "Help" },
  { href: "/faq", label: "FAQ" },
  { href: "/support", label: "Support" },
  { href: "/safety", label: "Safety" },
  { href: "/merch-guide", label: "Merch Guide" },
];

const companyLinks = [
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
  { href: "/community-guidelines", label: "Community Guidelines" },
  { href: "/report", label: "Report" },
];

/** Legal strip only — avoid repeating Support/Safety/Report names from columns above. */
const legalLinks = [
  { href: "/terms", label: "Terms" },
  { href: "/privacy", label: "Privacy" },
  { href: "/cookies", label: "Cookies" },
  { href: "/refund-policy", label: "Refund Policy" },
  { href: "/ticket-policy", label: "Ticket Policy" },
  { href: "/accessibility", label: "Accessibility" },
];

const FOOTER_SECTIONS = [
  { id: "discover", title: "Discover", links: discoverLinks },
  { id: "for-fans", title: "For Fans", links: forFansLinks },
  { id: "for-hosts", title: "For Hosts", links: forHostsLinks },
  { id: "resources", title: "Resources", links: resourcesLinks },
  { id: "company", title: "Company", links: companyLinks },
  { id: "legal", title: "Legal", links: legalLinks },
] as const;

const linkClass =
  "inline-flex min-h-11 items-center text-[0.95rem] font-semibold text-paper/80 transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: { href: string; label: string }[];
}) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-paper/60">
        {title}
      </p>
      <ul className="mt-3 space-y-1">
        {links.map((link) => (
          <li key={`${link.href}:${link.label}`}>
            <Link href={link.href} className={linkClass}>
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FooterAccordionSection({
  title,
  links,
  defaultOpen = false,
}: {
  title: string;
  links: { href: string; label: string }[];
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details
      className="group border-b border-paper/10 last:border-b-0"
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 py-3 text-sm font-bold uppercase tracking-[0.14em] text-paper/80 marker:content-none [&::-webkit-details-marker]:hidden">
        {title}
        <span
          className={cn(
            "text-base font-normal text-primary transition-transform",
            open && "rotate-45",
          )}
          aria-hidden
        >
          +
        </span>
      </summary>
      <ul className="space-y-1 pb-4">
        {links.map((link) => (
          <li key={`${link.href}:${link.label}`}>
            <Link
              href={link.href}
              className="flex min-h-11 items-center py-1 text-base font-semibold text-paper/80 transition-colors hover:text-primary"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </details>
  );
}

function FooterRoleCta() {
  const { user, loading, isImpersonating } = useAuth();
  const { isAdmin, hasHostWorkspace } = useHeaderAccess(user, isImpersonating);

  if (loading) return null;

  if (!user) {
    return (
      <Link href="/events" className="inline-flex text-sm font-semibold text-primary hover:underline">
        Explore events →
      </Link>
    );
  }
  if (isAdmin) {
    return (
      <Link href="/admin" className="inline-flex text-sm font-semibold text-primary hover:underline">
        Admin panel →
      </Link>
    );
  }
  if (hasHostWorkspace) {
    return (
      <Link href="/host" className="inline-flex text-sm font-semibold text-primary hover:underline">
        Host workspace →
      </Link>
    );
  }
  return (
    <Link href="/dashboard" className="inline-flex text-sm font-semibold text-primary hover:underline">
      Personal dashboard →
    </Link>
  );
}

export function SiteFooter() {
  const pathname = usePathname();
  if (isWorkspacePath(pathname)) return null;

  return (
    <footer className="mt-auto overflow-x-hidden bg-ink text-paper">
      <Container className="space-y-10 py-10 lg:space-y-12 lg:py-14">
        <div className="min-w-0 max-w-md space-y-4">
          <Logo variant="dark" height={28} />
          <p className="text-pretty text-sm leading-relaxed text-paper/75 sm:text-[0.95rem]">
            {brand.tagline}
          </p>
          <FooterRoleCta />
        </div>

        {/* Desktop columns */}
        <div className="hidden gap-8 sm:grid sm:grid-cols-2 lg:grid-cols-5 lg:gap-x-8">
          <FooterColumn title="Discover" links={discoverLinks} />
          <FooterColumn title="For Fans" links={forFansLinks} />
          <FooterColumn title="For Hosts" links={forHostsLinks} />
          <FooterColumn title="Resources" links={resourcesLinks} />
          <FooterColumn title="Company" links={companyLinks} />
        </div>

        {/* Mobile accordion */}
        <div className="sm:hidden" data-testid="footer-mobile-accordion">
          {FOOTER_SECTIONS.map((section) => (
            <FooterAccordionSection
              key={section.id}
              title={section.title}
              links={[...section.links]}
              defaultOpen={section.id === "discover"}
            />
          ))}
        </div>
      </Container>

      <div className="border-t border-paper/10">
        <Container className="flex flex-col gap-4 py-5 sm:gap-5 sm:py-6">
          <nav
            aria-label="Legal"
            className="hidden flex-wrap gap-x-4 gap-y-1 text-sm text-paper/70 sm:flex"
          >
            {legalLinks.map((link) => (
              <Link
                key={`${link.href}:${link.label}`}
                href={link.href}
                className="inline-flex min-h-11 items-center font-medium transition-colors hover:text-primary"
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <p className="text-sm text-paper/65">
            © {new Date().getFullYear()}{" "}
            <span className="text-paper/90">{brand.name}</span>. All rights
            reserved.
          </p>
        </Container>
      </div>
    </footer>
  );
}
