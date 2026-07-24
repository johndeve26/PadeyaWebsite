import Link from "next/link";

import { LegalSection } from "@/components/legal/LegalDocument";
import { brand } from "@/lib/brand";
import { legalToc } from "@/lib/legal/toc";

export const COOKIES_TOC = legalToc(
  { id: "overview", title: "Overview" },
  { id: "essential", title: "Essential storage" },
  { id: "auth", title: "Auth & session" },
  { id: "preferences", title: "Preferences & UX" },
  { id: "referral", title: "Ambassador referrals" },
  { id: "analytics", title: "Analytics" },
  { id: "marketing", title: "Marketing" },
  { id: "third-parties", title: "Third-party services" },
  { id: "controls", title: "Your controls" },
);

export function CookiesContent() {
  return (
    <>
      <LegalSection id="overview" title="Overview">
        <p>
          This Cookie Policy explains how {brand.name} uses cookies and similar
          technologies to keep the Platform signed-in, secure, and useful. On
          this page, &ldquo;cookies&rdquo; includes:
        </p>
        <ul>
          <li>HTTP cookies set in your browser</li>
          <li>
            <strong>localStorage</strong> and <strong>sessionStorage</strong>{" "}
            (browser storage that persists on your device)
          </li>
          <li>Other comparable on-device storage used for the same purposes</li>
        </ul>
        <p>
          For broader data practices, see the{" "}
          <Link href="/privacy">Privacy Policy</Link>.
        </p>
      </LegalSection>

      <LegalSection id="essential" title="Essential storage">
        <p>
          Essential storage is required for core functions: security, load
          balancing, fraud prevention basics, checkout flow continuity, and
          remembering choices the site needs to work. This includes critical{" "}
          <strong>localStorage</strong> and <strong>sessionStorage</strong>{" "}
          entries (for example sign-in state and checkout hints), not only HTTP
          cookies. Disabling or clearing essential storage can break login,
          checkout, or account access.
        </p>
        <p>
          {brand.name} does not currently rely on a separate in-product cookie
          consent banner; when we introduce optional analytics or marketing
          tags, we will describe them here and in the product.
        </p>
      </LegalSection>

      <LegalSection id="auth" title="Auth & session">
        <p>
          {brand.name} currently uses browser <strong>localStorage</strong> to
          keep you signed in and sends authentication tokens to our API using{" "}
          <strong>Authorization</strong> headers. We do not use traditional
          login session cookies for normal account access.
        </p>
        <p>
          Clearing <strong>site data</strong> for {brand.name} (including
          localStorage) will sign you out. Blocking HTTP cookies alone may{" "}
          <strong>not</strong> remove localStorage tokens or end your session.
        </p>
      </LegalSection>

      <LegalSection id="preferences" title="Preferences & UX">
        <p>
          We use localStorage and sessionStorage to remember UI and workflow
          choices so you do not reset them every visit. These are not
          traditional cookies but behave like browser storage used to remember
          preferences or improve the experience. Examples include:
        </p>
        <ul>
          <li>Theme preference (including dark mode)</li>
          <li>Host workspace context (active host, workspace mode)</li>
          <li>Notification sound preferences</li>
          <li>Discovery and location preferences where you opt in</li>
          <li>Short-lived checkout or registration hints in sessionStorage</li>
          <li>
            Progressive Web App (PWA) offline display cache for tickets or merch
            pickup where enabled
          </li>
          <li>Merch draft cart state while you browse an event store</li>
        </ul>
      </LegalSection>

      <LegalSection id="referral" title="Ambassador referrals">
        <p>
          When you visit an event or checkout link with an ambassador referral
          parameter, {brand.name} may set an HTTP cookie to attribute ticket or
          merch sales fairly to ambassadors.
        </p>
        <ul>
          <li>
            <strong>Name:</strong> <code>padeya_amb_ref_v1</code>
          </li>
          <li>
            <strong>Purpose:</strong> stores ambassador referral codes for event
            attribution
          </li>
          <li>
            <strong>Set when:</strong> you land with <code>?ref=</code> or{" "}
            <code>?amb=</code> on an event or merch page (including checkout
            URLs that carry those parameters)
          </li>
          <li>
            <strong>Behavior:</strong> last click wins per event; expires after
            30 days; <code>SameSite=Lax</code>; <code>path=/</code>
          </li>
        </ul>
        <p>At checkout, referral credit uses this order of precedence:</p>
        <ol>
          <li>Explicit ambassador code entered by the buyer</li>
          <li>Referral code from the link (<code>ref</code> / <code>amb</code>)</li>
          <li>The referral cookie, if still valid</li>
        </ol>
        <p>
          An explicit code at checkout always overrides a link or cookie. You
          can remove this cookie through browser cookie controls or by clearing
          site data for {brand.name}.
        </p>
      </LegalSection>

      <LegalSection id="analytics" title="Analytics">
        <p>
          We may use first-party analytics or marketing technologies where
          enabled to understand feature usage, fix funnels, and improve
          reliability. Analytics are used to operate and improve {brand.name},
          not to sell personal profiles as a product. We do not name specific
          third-party analytics or ad networks on this page unless they are
          actively in use; check in-product notices when additional tools are
          introduced.
        </p>
        <p>
          Where a market requires consent for non-essential analytics, we align
          collection with those expectations.
        </p>
      </LegalSection>

      <LegalSection id="marketing" title="Marketing">
        <p>
          Ambassador referral attribution (see above) supports outreach and
          commission programs you interact with through referral links. We may
          also use analytics or marketing technologies where enabled to measure
          campaign effectiveness, subject to the same privacy principles in our{" "}
          <Link href="/privacy">Privacy Policy</Link>.
        </p>
        <p>
          We do not claim exhaustive ad-tech coverage here. Optional marketing
          tags, when used, will be described in product notices and updated on
          this page.
        </p>
      </LegalSection>

      <LegalSection id="third-parties" title="Third-party services">
        <p>
          Payment partners, hosting, messaging delivery, and similar processors
          may set their own cookies or use browser storage when you use their
          flows.
        </p>
        <p>
          <strong>Paystack</strong> (and similar payment providers) may set
          their own cookies or use browser storage during payment processing on
          checkout. {brand.name} does not control Paystack&rsquo;s browser
          storage; those services are governed by their policies in addition to
          ours.
        </p>
      </LegalSection>

      <LegalSection id="controls" title="Your controls">
        <ul>
          <li>
            Use your browser&rsquo;s cookie settings to block or delete HTTP
            cookies (including ambassador referral cookies).
          </li>
          <li>
            Clear <strong>site data</strong> for {brand.name} to reset sign-in,
            preferences, localStorage, sessionStorage, and cookies together.
            This typically signs you out.
          </li>
          <li>
            You can clear localStorage and sessionStorage separately in
            developer or site-data tools if your browser supports it.
          </li>
          <li>
            Manage notification and email preferences in your account where
            available.
          </li>
          <li>
            Manage discovery location preference in the product or by clearing
            site data.
          </li>
          <li>
            Opt out of marketing communications where we offer those controls
            (for example email preferences).
          </li>
          <li>
            Questions: <Link href="/support">Support</Link> or{" "}
            <Link href="/contact">Contact</Link>.
          </li>
        </ul>
      </LegalSection>
    </>
  );
}
