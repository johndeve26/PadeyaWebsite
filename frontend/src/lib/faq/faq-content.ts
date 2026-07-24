import { brand } from "@/lib/brand";

export type FaqItem = {
  id: string;
  q: string;
  /** Plain text; optional markdown links: [label](/path) */
  a: string;
};

export type FaqCategory = {
  id: string;
  title: string;
  items: readonly FaqItem[];
};

export const FAQ_SEO = {
  title: `FAQ — Tickets, Hosts, Fan Passport & Support | ${brand.name}`,
  description: `Answers about ${brand.name}: tickets and checkout, guest purchases, Fan Passport, Fan Connect, hosting, QR check-in, merch, Ambassadors, sponsorships, refunds, safety, and support.`,
  path: "/faq",
} as const;

export const FAQ_CATEGORIES: readonly FaqCategory[] = [
  {
    id: "getting-started",
    title: "Getting Started",
    items: [
      {
        id: "what-is-padeya",
        q: `What is ${brand.name}?`,
        a: `${brand.name} is a technology platform and marketplace for event discovery, verified ticketing, host tools, fan identity, support, and related services. Fans explore listings, check out securely, and keep QR tickets ready for the door. Hosts run Event Studio, check-in, merch, Ambassadors, and sponsorship tools from one workspace. Unless expressly stated, ${brand.name} is not the organizer of third-party host events — hosts remain responsible for listings and on-site delivery. Start at [Events](/events), [For fans](/for-fans), [For hosts](/for-hosts), or [Terms](/terms).`,
      },
      {
        id: "who-can-use",
        q: `Who can use ${brand.name}?`,
        a: `Fans, hosts, ambassadors, and brands exploring sponsorships. Visitors can browse events and often buy tickets as guests. Creating a Fan Passport, hosting, Fan Connect, Ambassadors, and most account tools require signing up. See [For fans](/for-fans) and [For hosts](/for-hosts).`,
      },
      {
        id: "does-padeya-organize",
        q: `Does ${brand.name} organize the events I see?`,
        a: `Usually no. Listings are created by independent hosts. ${brand.name} provides the marketplace, ticketing, and tools. Hosts are responsible for listing accuracy, safety, venue readiness, and communicating changes or cancellations. Review details before you buy — see [Terms](/terms) and the [Safety Center](/safety).`,
      },
      {
        id: "account-to-buy",
        q: "Do I need an account to buy tickets?",
        a: `Not always. Many events support guest checkout so you can pay without signing in first. An account makes it easier to manage tickets, refunds, Fan Passport, and Fan Connect later. Guest buyers can claim tickets into an account after purchase.`,
      },
      {
        id: "mobile-use",
        q: `Can I use ${brand.name} on mobile?`,
        a: `Yes. ${brand.name} is built for phones and desktop. Buy tickets, open your QR at the door, and manage host or fan tools from a mobile browser.`,
      },
      {
        id: "is-pwa",
        q: `Is ${brand.name} a PWA?`,
        a: `Yes. ${brand.name} offers an installable progressive web app experience where your browser supports it, so ticket and mobile flows stay close at hand.`,
      },
    ],
  },
  {
    id: "tickets-checkout",
    title: "Tickets & Checkout",
    items: [
      {
        id: "how-buy-ticket",
        q: "How do I buy a ticket?",
        a: `Open an event from [Events](/events), choose ticket types, complete buyer and attendee details, apply a promo or ambassador code if you have one, then complete secure checkout. Tickets are issued only after payment is verified — not from the browser success page alone. See the [Ticket Policy](/ticket-policy).`,
      },
      {
        id: "where-find-ticket",
        q: "Where do I find my ticket?",
        a: `Signed-in buyers: Personal → Tickets (or your account tickets area). Guest buyers: use the confirmation email and secure claim link. After you claim into an account with the same email, tickets appear in your ticket list for door scan.`,
      },
      {
        id: "when-qr-issued",
        q: "When is my QR ticket issued?",
        a: `Only after payment is confirmed by a verified webhook (or a free-ticket server confirm). Pending or failed payments do not issue a door QR. Once issued, open the ticket pass for check-in.`,
      },
      {
        id: "buy-for-someone-else",
        q: "Can I buy tickets for someone else?",
        a: `Yes. Checkout supports buying for yourself, for someone else, or for a group. For gifts, enter the recipient’s details and choose whether the ticket email goes to them, you, or both.`,
      },
      {
        id: "buy-group",
        q: "Can I buy multiple tickets for a group?",
        a: `Yes. Select multiple quantities, then enter attendee details per ticket or reuse the same details for the whole group when the event allows it.`,
      },
      {
        id: "promo-codes",
        q: "Can I use promo codes?",
        a: `Yes, when a host has an active promo or ambassador code. Enter it at checkout before you pay. Codes attach to the pending order; discounts and ambassador rewards finalize only after verified payment.`,
      },
      {
        id: "payment-pending",
        q: "Why is my payment pending?",
        a: `Checkout creates a pending order, then the payment provider confirms the charge. Until verification completes, tickets stay unissued. Refresh your confirmation email or ticket list after a short wait. If it stays stuck, contact [Support](/support) with your order reference.`,
      },
      {
        id: "payment-fails",
        q: "What happens if payment fails?",
        a: `No ticket QR is issued. You can retry checkout from the event page. If you were charged but see no ticket, open a ticket at [Support](/support) with the payment reference — never rely on a success screen alone.`,
      },
    ],
  },
  {
    id: "guest-checkout",
    title: "Guest Checkout",
    items: [
      {
        id: "checkout-without-account",
        q: "Can I checkout without an account?",
        a: `Yes for ticket purchases on events that allow guest checkout. You enter buyer details, complete payment, and receive confirmation by email. Guest checkout does not require login before payment. Merch-only or some bundle flows may still require an account.`,
      },
      {
        id: "guest-receive-ticket",
        q: "How do I receive my ticket as a guest?",
        a: `After verified payment, ${brand.name} emails your receipt and a secure claim link to the buyer email you provided. Use that link (and any ticket delivery options you chose) to open or claim your QR.`,
      },
      {
        id: "account-after-buying",
        q: "Can I create an account after buying?",
        a: `Yes. Register with the same email you used at checkout, or follow the claim flow from your confirmation email. Matching an existing account by email does not auto-log you in for security.`,
      },
      {
        id: "claim-guest-ticket",
        q: "Can I claim my guest ticket later?",
        a: `Yes. Use the secure claim link from your confirmation email, or create/sign in with the same email and claim when prompted. Claiming attaches tickets to your account so they stay in Personal → Tickets.`,
      },
      {
        id: "wrong-email-guest",
        q: "What if I entered the wrong email?",
        a: `Contact [Support](/support) quickly with your order or payment reference, full name, and the correct email. Support can help route delivery when ownership can be verified. Double-check the email before you pay next time.`,
      },
    ],
  },
  {
    id: "events-discovery",
    title: "Events & Discovery",
    items: [
      {
        id: "events-near-me",
        q: "How do I find events near me?",
        a: `Browse [Events](/events) or open [Near me](/events/near-me). Allow location when prompted, or search by city/area to surface nights close to you.`,
      },
      {
        id: "location-search",
        q: "How does location search work?",
        a: `Discovery uses the location you share or type, plus listing metadata hosts set (city, venue area, online). Results prioritize relevant nearby or matching places — not every listing worldwide.`,
      },
      {
        id: "browse-calendar",
        q: "Can I browse events by calendar?",
        a: `Yes. Use date filters and calendar-style browsing on the events experience to jump to a night or range that fits your schedule.`,
      },
      {
        id: "events-on-map",
        q: "Can I view events on a map?",
        a: `Where map views are available in discovery, you can explore listings geographically. Exact street addresses may stay hidden until the host’s reveal rules allow it.`,
      },
      {
        id: "location-after-payment",
        q: "What does “location revealed after payment” mean?",
        a: `Some hosts protect precise venue or online join details until you buy (or until another reveal rule like event day). You still see enough to decide — city/area or that it’s online — then the full location unlocks for ticket holders per the event’s settings.`,
      },
      {
        id: "padeya-picks",
        q: `What are ${brand.name} Picks?`,
        a: `${brand.name} Picks are curated spotlights on the homepage and events surfaces — featured nights the platform highlights so you can discover standout listings faster.`,
      },
    ],
  },
  {
    id: "fan-passport",
    title: "Fan Passport",
    items: [
      {
        id: "what-fan-passport",
        q: "What is Fan Passport?",
        a: `Fan Passport is your fan identity on ${brand.name} — public-safe profile, badges, attended nights, and reviews tied to real attendance. Learn more on [For fans](/for-fans) or open Fan Passport from your account.`,
      },
      {
        id: "public-passport",
        q: "What appears on my public Fan Passport?",
        a: `Only what your visibility settings allow: typically display name, avatar, tagline, and public badges or nights you choose to show. Private tickets, messages, payment details, and hidden fields stay off the public profile.`,
      },
      {
        id: "edit-passport",
        q: "Can I edit my Fan Passport?",
        a: `Yes. Update display name, bio/tagline, avatar, and privacy controls from Passport settings in your account.`,
      },
      {
        id: "passport-visibility",
        q: "Can I control who sees my profile?",
        a: `Yes. Passport visibility settings let you choose what is public. You control the profile surface — it is not an automatic dump of every ticket or message.`,
      },
      {
        id: "what-are-badges",
        q: "What are badges?",
        a: `Badges are marks on your Passport that reflect activity over time — such as nights attended or other eligible milestones. Some badges update after verified check-in or paid activity, not from a frontend success page alone.`,
      },
      {
        id: "share-passport",
        q: "Can I share my Fan Passport?",
        a: `Yes. Share your public Passport link when your profile is visible. Recipients only see public-safe fields you allow.`,
      },
    ],
  },
  {
    id: "fan-connect",
    title: "Fan Connect",
    items: [
      {
        id: "what-fan-connect",
        q: "What is Fan Connect?",
        a: `Fan Connect is an optional way to meet people around shared events and scenes — with privacy, block, and report controls. It is connection-oriented, not a public attendee list. See [For fans](/for-fans) and the [Safety Center](/safety).`,
      },
      {
        id: "connect-suggestions",
        q: "How are people suggested to me?",
        a: `Suggestions come from shared event context and interests you both care about — for example people going to the same nights — within your Connect settings. ${brand.name} does not expose a raw public roster of every attendee.`,
      },
      {
        id: "connect-nearby",
        q: "Can I connect with people near me?",
        a: `Nearby discovery is available only where your settings allow it. Location-aware Connect stays optional and privacy-safe — never forced exposure.`,
      },
      {
        id: "block-report",
        q: "Can I block or report someone?",
        a: `Yes. Use block and report tools in Fan Connect and messaging. For broader safety help, visit the [Safety Center](/safety) or [Support](/support).`,
      },
      {
        id: "turn-connect-off",
        q: "Can I turn Fan Connect off?",
        a: `Yes. Disable or tighten Fan Connect from Connect settings so you stop receiving suggestions or connection requests according to your preferences.`,
      },
      {
        id: "no-suggestions",
        q: "Why am I not seeing suggestions?",
        a: `Common reasons: Connect is off, privacy settings are strict, you have few shared upcoming events, or nearby mode is disabled. Attend or follow more nights, then check Connect settings again.`,
      },
    ],
  },
  {
    id: "hosts-events",
    title: "Hosts & Event Creation",
    items: [
      {
        id: "become-host",
        q: "How do I become a host?",
        a: `Start host onboarding from [For hosts](/for-hosts) or your account’s Become a host flow. After onboarding, use Host workspace for Event Studio, tickets, check-in, merch, Ambassadors, and sponsorships.`,
      },
      {
        id: "host-responsibilities",
        q: "What are hosts responsible for?",
        a: `Hosts are independent organizers. You are responsible for listing accuracy, safety, venue readiness, permits, crowd control, age restrictions, accessibility arrangements, emergency planning, and communicating changes, cancellations, entry rules, and refund terms. ${brand.name} provides the marketplace and tools, and may moderate listings for safety or policy risk. See [Terms](/terms) and [Safety](/safety).`,
      },
      {
        id: "create-event",
        q: "How do I create an event?",
        a: `Open Host → Create event / Event Studio. Add details, ticket types, policies, and media, then publish when ready. Fees and buyer totals appear in host and checkout flows before you go live.`,
      },
      {
        id: "paid-free-tickets",
        q: "Can I create paid and free tickets?",
        a: `Yes. Create free and paid ticket types in Event Studio. Free tickets still follow issuance rules on the server; paid tickets issue only after verified payment.`,
      },
      {
        id: "vip-table-tickets",
        q: "Can I create VIP or table tickets?",
        a: `Yes. Use multiple ticket types with different names, prices, quantities, and descriptions — including VIP, tables, or other packages your night needs.`,
      },
      {
        id: "add-team",
        q: "Can I add my team?",
        a: `Yes. Invite teammates from Host → Team with role-based access so scanners, merch desk, and ops staff only get what they need.`,
      },
      {
        id: "multiple-events",
        q: "Can I manage multiple events?",
        a: `Yes. Host workspace lists your events so you can draft, publish, check in, and report across many nights from one place.`,
      },
      {
        id: "edit-after-publish",
        q: "Can I edit an event after publishing?",
        a: `Yes, within host edit rules. You can update details and inventory as allowed; some fields are protected after sales start. Sold tickets and payment history are never casually rewritten.`,
      },
    ],
  },
  {
    id: "qr-checkin",
    title: "QR Check-in & Entry",
    items: [
      {
        id: "how-qr-checkin",
        q: "How does QR check-in work?",
        a: `Each paid (or free-confirmed) ticket carries a signed QR. Door staff scan it with host check-in tools. A valid scan marks attendance for that ticket.`,
      },
      {
        id: "staff-scan",
        q: "Can staff scan tickets?",
        a: `Yes. Hosts invite scanners/team members with check-in access so staff can scan at the door without full host admin rights.`,
      },
      {
        id: "after-checkin",
        q: "What happens when a ticket is checked in?",
        a: `The ticket moves to a checked-in state for that entry. Attendance can feed Fan Passport history. Re-scanning the same ticket does not create a fresh valid entry.`,
      },
      {
        id: "qr-reuse",
        q: "Can a QR code be reused?",
        a: `No. A checked-in QR is not meant for multiple entries. If a code is lost or compromised, hosts/support may revoke or regenerate according to ticket tools — see the [Ticket Policy](/ticket-policy).`,
      },
      {
        id: "guest-cant-find-ticket",
        q: "What if a guest cannot find their ticket?",
        a: `Ask them to open the confirmation email, claim link, or Personal → Tickets. Staff can look up by order/attendee tools when available. If payment never verified, there is no QR yet — send them to [Support](/support) with the payment reference.`,
      },
    ],
  },
  {
    id: "merch-vault",
    title: "Merch & Vault",
    items: [
      {
        id: "hosts-sell-merch",
        q: "Can hosts sell merch?",
        a: `Yes. Merch Studio lets hosts sell event add-ons, standalone products, post-event drops, and Vault exclusives, and manage pickup fulfillment. See [Merch guide](/merch-guide) for formats and flows.`,
      },
      {
        id: "post-event-drops",
        q: "What are post-event merch drops?",
        a: `Hosts can run merch tied to an event timeline — including drops after the night for eligible fans (checked-in, ticket buyers, VIPs, or Vault members). Learn more on [Merch guide](/merch-guide).`,
      },
      {
        id: "what-is-vault",
        q: "What is Vault?",
        a: `Vault is exclusive host content fans unlock by rules the host sets — for example follow, ticket, attendance, VIP, invite, or purchase. Public pages show teasers; full media stays gated until access is granted.`,
      },
      {
        id: "unlock-vault",
        q: "How do fans unlock Vault content?",
        a: `Meet the item’s access rule (ticket, attendance, purchase, invite, and similar). Paid unlocks grant access only after verified payment. Unlocked items appear in your Vault purchases area.`,
      },
      {
        id: "vault-public",
        q: "Are Vault items public?",
        a: `Teasers can be public on a host’s Vault catalog. Locked media and private files are not shown publicly. Purchased or granted access stays with the entitled fan.`,
      },
      {
        id: "merch-linked-event",
        q: "Can merch be linked to an event?",
        a: `Yes. Hosts can attach merch to events so fans buy night-related products from the event page, checkout add-ons, or host storefront. Overview: [Merch guide](/merch-guide).`,
      },
    ],
  },
  {
    id: "ambassadors",
    title: "Ambassadors",
    items: [
      {
        id: "ambassador-campaigns",
        q: "What are ambassador campaigns?",
        a: `Campaigns let hosts (and sometimes the platform) reward fans who promote events with tracked links or codes. Browse [Ambassadors](/ambassadors) to learn how joining works.`,
      },
      {
        id: "fans-promote",
        q: "How do fans promote events?",
        a: `Join an open or invited campaign, then share your unique link or code. Attribution can also follow a referral cookie window when the campaign allows it. Explicit checkout codes usually win over cookies.`,
      },
      {
        id: "rewards-tracked",
        q: "How are rewards tracked?",
        a: `Clicks and attributions are recorded when someone lands or checks out via your link/code. Commissions and rewards finalize only after a verified paid sale — never from a frontend success page. Self-referral is blocked.`,
      },
      {
        id: "rewards-paid",
        q: "When are rewards paid?",
        a: `After verified paid conversions clear campaign hold and payout rules. Status appears in ambassador dashboards. Refunds or fraud reversals can reverse rewards.`,
      },
      {
        id: "hosts-create-campaigns",
        q: "Can hosts create ambassador campaigns?",
        a: `Yes. Hosts launch campaigns from Host → Ambassadors, set commission and visibility, and track leaderboards. Fans never gain host staff access just by promoting.`,
      },
    ],
  },
  {
    id: "sponsorships",
    title: "Sponsorships",
    items: [
      {
        id: "sponsorship-marketplace",
        q: "What is the sponsorship marketplace?",
        a: `A public place for brands to discover hosts and sponsorship slots, then send inquiries. Hosts publish packages; brands browse and reach out. Start at [Sponsorships](/sponsorships) or [For hosts](/for-hosts).`,
      },
      {
        id: "brands-sponsor",
        q: "Can brands sponsor events?",
        a: `Yes. Brands explore host packages on the marketplace and submit sponsorship inquiries for slots that fit their goals.`,
      },
      {
        id: "hosts-receive-inquiries",
        q: "Can hosts receive sponsorship inquiries?",
        a: `Yes. When you publish sponsorship packages, inquiries arrive in Host → Sponsorships for review and status updates.`,
      },
      {
        id: "sponsorship-requests",
        q: "How do sponsorship requests work?",
        a: `A brand submits an inquiry against a host slot or package. The host reviews and updates status in the host sponsorship tools. Deals stay between host and brand — ${brand.name} provides the marketplace workflow.`,
      },
    ],
  },
  {
    id: "payments-refunds",
    title: "Payments, Refunds & Fees",
    items: [
      {
        id: "payment-methods",
        q: "What payment methods are supported?",
        a: `Checkout runs through secure payment partners. Available methods depend on your region (cards and other supported options). The checkout page shows what you can use before you pay.`,
      },
      {
        id: "payments-secure",
        q: "Are payments secure?",
        a: `Yes. Card payments are processed securely. ${brand.name} issues tickets and commits inventory only after verified payment webhooks — not from trusting the browser alone.`,
      },
      {
        id: "how-refunds",
        q: "How do refunds work?",
        a: `Refund eligibility depends on event status, host policy, product type (tickets, merch, Vault), and settlement. Cancelled events and verified duplicate charges are common refund cases; change of mind after an entry-ready ticket issues usually is not. Start from Personal → Refunds or read the [Refund Policy](/refund-policy). Guest buyers can use [Support](/support) with their order reference.`,
      },
      {
        id: "host-refund-rules",
        q: "Can hosts set refund rules?",
        a: `Hosts configure event policies within platform rules and should communicate changes clearly. Buyer-facing outcomes still follow the published [Refund Policy](/refund-policy) and [Ticket Policy](/ticket-policy).`,
      },
      {
        id: "what-fees",
        q: "What fees apply?",
        a: `${brand.name} is free for fans to join. Hosts typically pay platform fees on successful sales. Any buyer-facing amounts appear in checkout before you pay — no surprise line items after confirmation. See [Pricing](/pricing) and host finance views for live host rates.`,
      },
      {
        id: "when-payouts",
        q: "When are payouts handled?",
        a: `Successful sales settle through the host payout flow with ledger visibility in Host finance tools. Timing depends on settlement and payout status in your host workspace. See [Pricing](/pricing) for fee context.`,
      },
    ],
  },
  {
    id: "account-safety",
    title: "Account, Safety & Privacy",
    items: [
      {
        id: "account-settings",
        q: "How do I change my account settings?",
        a: `Sign in and open your account/settings area to update profile, password, and related preferences. Passport and Connect have their own privacy controls.`,
      },
      {
        id: "notifications",
        q: "How do I control notifications?",
        a: `Use notification preferences in your account settings to choose which emails or alerts you receive for tickets, messages, and product updates.`,
      },
      {
        id: "report-abuse",
        q: "How do I report abuse?",
        a: `Use in-product report tools where available, or open the [Safety Center](/safety) and [Support](/support). Include links, usernames, and context so the team can act.`,
      },
      {
        id: "how-blocks",
        q: "How do blocks work?",
        a: `Blocking limits that person’s ability to connect or message you according to product rules. You can manage blocks from Connect/safety controls. See the [Safety Center](/safety).`,
      },
      {
        id: "account-restricted",
        q: "What happens if my account is restricted?",
        a: `Restrictions can limit login, hosting, Ambassadors, Connect, or other actions depending on the case. You will see status messaging in-product. Appeals go through [Account appeal](/account/appeal) when available.`,
      },
      {
        id: "how-appeals",
        q: "How do appeals work?",
        a: `If your account is restricted or suspended, submit an appeal from [Account appeal](/account/appeal) with a clear explanation. Support reviews appeals separately from ordinary ticket help.`,
      },
      {
        id: "private-data-public",
        q: "Is my private data shown publicly?",
        a: `No. Payment secrets, private messages, exact shipping details, locked Vault media, and hidden venue streets are not exposed on public profiles or catalogs. Public Passport and listings only show fields allowed by privacy and reveal rules. See [Privacy](/privacy) and [Safety](/safety).`,
      },
    ],
  },
  {
    id: "support-appeals",
    title: "Support & Appeals",
    items: [
      {
        id: "contact-support",
        q: "How do I contact support?",
        a: `Open the [Support Center](/support) to browse options, or create a tracked ticket at [/support/new](/support/new). For guides first, visit the [Help Center](/help).`,
      },
      {
        id: "who-create-ticket",
        q: "Who can create a support ticket?",
        a: `Fans, hosts, and visitors. Guests can open tickets with contact details; signed-in users can also manage tickets from their dashboard support area.`,
      },
      {
        id: "track-ticket",
        q: "How do I track my ticket?",
        a: `Use [Track a ticket](/support/tickets/lookup) with your email and reference, or open My tickets when signed in. Keep your ticket number from the confirmation email.`,
      },
      {
        id: "hosts-contact-support",
        q: "Can hosts contact support?",
        a: `Yes. Use [Support](/support) or Host → Support from your workspace for payouts, events, check-in, and other host ops issues.`,
      },
      {
        id: "appeal-restriction",
        q: "How do I appeal a restriction or suspension?",
        a: `Go to [Account appeal](/account/appeal), explain what happened, and submit. For general product help that is not an account restriction, open a normal ticket at [Support](/support).`,
      },
    ],
  },
] as const;

/** Flattened list for search indexes and FAQPage JSON-LD. */
export function allFaqItems(): FaqItem[] {
  return FAQ_CATEGORIES.flatMap((c) => [...c.items]);
}

export function faqAnswerPlainText(answer: string): string {
  return answer.replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1");
}

export function filterFaqCategories(
  categories: readonly FaqCategory[],
  query: string,
): FaqCategory[] {
  const q = query.trim().toLowerCase();
  if (!q) return categories.map((c) => ({ ...c, items: [...c.items] }));

  return categories
    .map((category) => ({
      ...category,
      items: category.items.filter(
        (item) =>
          item.q.toLowerCase().includes(q) ||
          faqAnswerPlainText(item.a).toLowerCase().includes(q) ||
          category.title.toLowerCase().includes(q),
      ),
    }))
    .filter((category) => category.items.length > 0);
}
