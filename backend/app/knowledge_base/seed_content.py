"""Seeded Help Center articles — real Pàdéyá product guidance (no placeholders)."""

from __future__ import annotations

SAMPLE_ARTICLES: list[dict] = [
    {
        "title": "How to buy a ticket on Pàdéyá",
        "slug": "how-to-buy-tickets",
        "category": "buying-tickets",
        "tags": ["tickets", "how-to", "getting-started", "fans"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "visitor"],
        "featured": True,
        "featured_sort": 1,
        "video_url": None,
        "seo_title": "How to buy a ticket on Pàdéyá | Help Center",
        "seo_description": (
            "Find an event, choose a tier, and complete checkout. "
            "Tickets issue only after verified payment."
        ),
        "excerpt": (
            "Browse an official event page, pick a tier, pay through checkout, "
            "then open My Tickets for your signed QR."
        ),
        "body": """## Buy on the official event page

Pàdéyá issues tickets **only after verified payment**. Always buy from the official event page — never via random bank transfers or “slots” in group chats.

### Steps

1. Open [Events](/events) and pick a night
2. Choose a ticket tier (early bird, general, VIP, or other published types)
3. Complete checkout with a supported payment method
4. Open **My Tickets** — your signed QR is ready for the door

### Before you pay

- Confirm venue timing, start time, and the host’s refund rules
- Prefer hosts with a clear [Legacy Page](/hosts)
- Skip off-platform “deals” that ask for payment proof only

### If something goes wrong

Search this Help Center first, then open a tracked case in the [Support Center](/support).

::cta{label="Browse events"; href="/events"}
""",
    },
    {
        "title": "How guest checkout works",
        "slug": "how-guest-checkout-works",
        "category": "guest-checkout",
        "tags": ["tickets", "how-to", "fans", "getting-started"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "visitor"],
        "featured": True,
        "featured_sort": 2,
        "video_url": None,
        "seo_title": "Guest checkout on Pàdéyá | Help Center",
        "seo_description": (
            "Buy without an account using your email, then access tickets "
            "with the order email and references you receive."
        ),
        "excerpt": (
            "Checkout as a guest with a valid email. Keep your confirmation — "
            "you’ll need it to find tickets and talk to Support."
        ),
        "body": """## Guest checkout

You can buy without creating an account when guest checkout is available on the event.

### Steps

1. Open the official event page and choose ticket quantities
2. Enter a real email you can access — tickets and recovery use this address
3. Complete payment through the hosted checkout flow
4. Use the confirmation email and order reference to open tickets later

### Tips

- Creating an account later can make **My Tickets** easier to manage
- Guest buyers still follow the same [Ticket Policy](/ticket-policy) and [Refund Policy](/refund-policy)
- Never share one-time codes or payment references in public chats

::cta{label="Explore events"; href="/events"}
""",
    },
    {
        "title": "How to find your QR ticket",
        "slug": "how-to-find-your-qr-ticket",
        "category": "my-tickets-and-qr",
        "tags": ["tickets", "check-in", "how-to", "fans"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "visitor"],
        "featured": True,
        "featured_sort": 3,
        "video_url": None,
        "seo_title": "Find your QR ticket | Pàdéyá Help",
        "seo_description": (
            "Open My Tickets when signed in, or recover guest tickets "
            "with the email used at checkout."
        ),
        "excerpt": (
            "Signed-in buyers use My Tickets. Guest buyers recover with "
            "the checkout email and order details."
        ),
        "body": """## Where your QR lives

Tickets carry a **signed QR payload**. Door staff should scan the live ticket — not a random screenshot from chat.

### If you have an account

1. Sign in
2. Open [My Tickets](/dashboard/tickets)
3. Select the event and show the QR at the door

### If you checked out as a guest

1. Open the confirmation email from checkout
2. Follow the ticket access link, or use Support lookup with your email and ticket/order reference
3. Keep brightness up and avoid cropped screenshots when possible

### Door tip

Hosts validate signed QRs. Reused images and fake screenshots fail validation.

::cta{label="Open My Tickets"; href="/dashboard/tickets"}
""",
    },
    {
        "title": "How to buy a ticket for someone else",
        "slug": "how-to-buy-ticket-for-someone-else",
        "category": "buying-tickets",
        "tags": ["tickets", "how-to", "fans"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "visitor"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Buy a ticket for someone else | Pàdéyá Help",
        "seo_description": (
            "Assign attendee details during checkout when the event allows "
            "gift or recipient fields."
        ),
        "excerpt": (
            "Use recipient/attendee fields at checkout when available, "
            "and share ticket access safely with the guest."
        ),
        "body": """## Buying for a friend

Some events let you name attendees or gift tickets during checkout.

### Steps

1. Choose the ticket quantity on the official event page
2. Fill attendee or recipient fields when the form asks for them
3. Complete payment — tickets issue only after verification
4. Share access carefully: prefer the guest viewing their own ticket screen at the door

### Notes

- Entry rules (age, ID, dress code) still apply to the person attending
- Refund and transfer rules follow the host listing plus [Ticket Policy](/ticket-policy)
- Don’t post QR images in public group chats

::cta{label="Browse events"; href="/events"}
""",
    },
    {
        "title": "How refunds work",
        "slug": "how-refunds-work",
        "category": "refunds",
        "tags": ["tickets", "how-to", "fans", "hosts"],
        "content_type": "faq",
        "difficulty": "beginner",
        "audiences": ["fan", "host", "visitor"],
        "featured": True,
        "featured_sort": 4,
        "video_url": None,
        "seo_title": "How refunds work on Pàdéyá | Help Center",
        "seo_description": (
            "Refund eligibility depends on host rules, event status, "
            "and the Refund Policy. Request via dashboard or Support."
        ),
        "excerpt": (
            "Read the host refund rules and platform Refund Policy, "
            "then request through My orders or Support with your order reference."
        ),
        "body": """## Refunds on Pàdéyá

Refunds are governed by the host’s published rules and the platform [Refund Policy](/refund-policy). Pàdéyá is the marketplace technology — hosts set event-level refund terms unless a policy exception applies.

### Common paths

1. Open [My orders](/dashboard/orders) (signed in) and check refund options for that order
2. If the event was cancelled or rescheduled, follow the instructions on the order and listing
3. For guest checkout, use your confirmation email and open [Support](/support) with the order reference

### What to include

- Order or ticket reference
- Event name and date
- Why you’re requesting a refund

### Timing

Processing times vary by payment provider and bank. Platform and processor fees may be non-refundable where the policy says so.

::cta{label="Read Refund Policy"; href="/refund-policy"}
""",
    },
    {
        "title": "How to create your Fan Passport",
        "slug": "how-to-create-fan-passport",
        "category": "fan-passport",
        "tags": ["fans", "getting-started", "how-to"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Create a Fan Passport | Pàdéyá Help",
        "seo_description": (
            "Set up your Fan Passport profile, badges, and privacy controls "
            "on Pàdéyá."
        ),
        "excerpt": (
            "Register, open Fan Passport, set what’s public, and keep "
            "privacy controls in sync with Fan Connect."
        ),
        "body": """## Fan Passport basics

Fan Passport is your fan identity on Pàdéyá — attended nights, badges, and privacy-safe profile fields.

### Steps

1. [Create an account](/register) or sign in
2. Open [Fan Passport](/dashboard/passport) (or the public [Fans](/fans) overview)
3. Add a display name and photo you’re comfortable sharing
4. Review privacy settings before enabling directory or Connect features

### Tips

- Public fields should stay safe for strangers at events
- You can tighten visibility later in privacy settings

::cta{label="Open Fan Passport"; href="/dashboard/passport"}
""",
    },
    {
        "title": "How Fan Connect suggestions work",
        "slug": "how-fan-connect-suggestions-work",
        "category": "fan-connect",
        "tags": ["fans", "how-to", "safety"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Fan Connect suggestions | Pàdéyá Help",
        "seo_description": (
            "Understand how Fan Connect suggestions appear and how to "
            "control privacy, blocks, and reports."
        ),
        "excerpt": (
            "Suggestions use shared events and interests you opt into. "
            "You control visibility, blocks, and reports."
        ),
        "body": """## Fan Connect

Fan Connect helps you meet people around shared nights — with controls you own.

### How suggestions appear

- Shared upcoming or attended events
- Interests and preferences you’ve enabled
- Privacy settings that decide what others can see

### Stay in control

1. Open [Fan Connect](/connect) and your Connect settings
2. Review who can message or request you
3. Block or report anyone who crosses the line — see [Safety](/safety)

### Important

Fan Connect is not a dating guarantee and does not replace local safety judgment. Meet in public places when you choose to meet offline.

::cta{label="Open Fan Connect"; href="/connect"}
""",
    },
    {
        "title": "How to block or report someone",
        "slug": "how-to-block-or-report-someone",
        "category": "reports-and-blocking",
        "tags": ["safety", "how-to", "fans"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "host", "visitor", "ambassador", "sponsor"],
        "featured": True,
        "featured_sort": 5,
        "video_url": None,
        "seo_title": "Block or report on Pàdéyá | Help Center",
        "seo_description": (
            "Block users in messaging or Fan Connect, and file reports "
            "through Safety and Support when needed."
        ),
        "excerpt": (
            "Use in-product block tools first. For abuse, fraud, or safety "
            "concerns, file a report — and call local authorities for emergencies."
        ),
        "body": """## Block and report

### Immediate danger

If you are in immediate danger, contact **local emergency services** first. Pàdéyá Support cannot replace police or emergency responders.

### Block someone

1. Open the conversation or profile controls in Messages / Fan Connect
2. Choose **Block**
3. Confirm — blocked users shouldn’t be able to keep messaging you through that channel

### Report abuse

1. Open the [Report](/report) page or in-product report action
2. Pick the right category (user, message, event, fraud, safety)
3. Include ticket/message/event references when you have them
4. For account follow-up, open a [Support](/support) ticket under Messaging / report abuse

::cta{label="Safety Center"; href="/safety"}
""",
    },
    {
        "title": "How to become a host",
        "slug": "how-to-become-a-host",
        "category": "becoming-a-host",
        "tags": ["hosts", "getting-started", "how-to"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["host", "visitor"],
        "featured": True,
        "featured_sort": 6,
        "video_url": None,
        "seo_title": "Become a host on Pàdéyá | Help Center",
        "seo_description": (
            "Start host onboarding, complete your profile, and prepare "
            "to publish events with tickets and check-in."
        ),
        "excerpt": (
            "Complete host onboarding, set up your profile, then create "
            "your first event when you’re ready to sell."
        ),
        "body": """## Host onboarding

Hosts on Pàdéyá are independent organizers. You’re responsible for listing accuracy, venue readiness, and communicating changes to buyers.

### Steps

1. Create an account and open [Host onboarding](/host/onboarding)
2. Complete required profile details for your host workspace
3. Review [pricing](/pricing) and fee expectations
4. Create your first draft event when ready

### After you’re approved / ready

- Publish clear refund and ticket policies before selling
- Train door staff on QR check-in
- Prefer on-platform Ambassadors and sponsorships for auditable growth

::cta{label="Become a host"; href="/host/onboarding"}
""",
    },
    {
        "title": "How to create and publish an event",
        "slug": "create-your-first-event",
        "category": "creating-events",
        "tags": ["hosts", "how-to", "getting-started"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["host"],
        "featured": True,
        "featured_sort": 7,
        "video_url": None,
        "seo_title": "Create and publish an event | Pàdéyá Host Help",
        "seo_description": (
            "Draft venue, tickets, and policies, then publish when your "
            "host checklist is complete."
        ),
        "excerpt": (
            "Set the room, ticket tiers, and policies — then publish when "
            "your checklist is green."
        ),
        "body": """## From draft to live

1. Open [Host events](/host/events) and create a draft
2. Add venue, start time, cover, and description
3. Configure ticket types, pricing, and inventory
4. Publish refund and ticket policies before sale
5. Go live when the publish checklist is complete

### After publish

Share the official event URL only. Prefer on-platform Ambassadors and sponsorships so conversions stay auditable.

::cta{label="Host events"; href="/host/events"}
""",
    },
    {
        "title": "How QR check-in works",
        "slug": "how-qr-check-in-works",
        "category": "qr-check-in",
        "tags": ["check-in", "hosts", "tickets", "how-to"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["host"],
        "featured": True,
        "featured_sort": 8,
        "video_url": None,
        "seo_title": "QR check-in for hosts | Pàdéyá Help",
        "seo_description": (
            "Scan signed ticket QR codes at the door with host desk tools. "
            "Screenshots alone are not proof."
        ),
        "excerpt": (
            "Use Tickets & Entry tools to scan signed QRs. Train staff — "
            "no exceptions for VIP photo-only “proof.”"
        ),
        "body": """## Door check-in on Pàdéyá

Tickets carry a **signed QR payload**. Door staff should scan with host desk tools — not accept photo-only proof from chats.

### Best practices

1. Open **Tickets & Entry** / [Host desk](/host/desk) on a charged device before doors
2. Train staff to scan every guest
3. Keep refund and ticket policies published before sale
4. Escalate disputes through [Support](/support) so history stays documented

### Why scanning matters

Off-platform screenshots and reused images fail validation. Signed QRs protect fans and hosts when the room fills.

::cta{label="Open host desk"; href="/host/desk"}
""",
    },
    {
        "title": "How hosts add team members",
        "slug": "how-hosts-add-team-members",
        "category": "host-team",
        "tags": ["hosts", "how-to"],
        "content_type": "how_to",
        "difficulty": "intermediate",
        "audiences": ["host"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Add host team members | Pàdéyá Help",
        "seo_description": (
            "Invite staff with the right permissions for desk, messaging, "
            "and event ops — without sharing your password."
        ),
        "excerpt": (
            "Invite teammates from host settings, assign roles, and revoke "
            "access when a shift ends."
        ),
        "body": """## Host team

Don’t share your personal login. Invite staff with scoped permissions.

### Steps

1. Open host team / invites in your [host workspace](/host)
2. Send an invite to the teammate’s email
3. Assign a role that matches the job (desk, messaging, ops)
4. Remove access when someone leaves

### Security

- Prefer unique accounts per person
- Sign out of shared devices after desk shifts
- Escalate payout or finance questions only through authorized roles

::cta{label="Open host workspace"; href="/host"}
""",
    },
    {
        "title": "How merch and post-event drops work",
        "slug": "how-merch-and-post-event-drops-work",
        "category": "merch",
        "tags": ["merch", "fans", "hosts", "how-to"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "host", "visitor"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Merch and post-event drops | Pàdéyá Help",
        "seo_description": (
            "Buy host merch with tickets or as standalone drops, and "
            "understand pickup versus delivery instructions from the host."
        ),
        "excerpt": (
            "Merch may sell with tickets or after the night. Follow the "
            "host’s pickup or fulfilment instructions on the order."
        ),
        "body": """## Merch on Pàdéyá

Hosts can sell merch alongside tickets or as post-event drops.

### For fans

1. Add merch during checkout or from the host/event merch section
2. Complete payment — fulfilment starts after verified payment
3. Follow pickup windows or shipping notes on your order

### For hosts

Use Merch Studio in the host workspace to configure products, inventory, and pickup rules. Keep descriptions accurate.

### Refunds

Merch refunds follow host rules and the [Refund Policy](/refund-policy).

::cta{label="Browse events"; href="/events"}
""",
    },
    {
        "title": "How Vault content works",
        "slug": "how-vault-content-works",
        "category": "vault",
        "tags": ["vault", "fans", "hosts", "how-to"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "host"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Vault content on Pàdéyá | Help Center",
        "seo_description": (
            "Vault items are host-published content with access rules "
            "such as ticket unlock or follow unlock."
        ),
        "excerpt": (
            "Unlock Vault items based on the host’s rules — ticket, follow, "
            "or other published access paths."
        ),
        "body": """## Vault

Vault is host-published content (media, drops, archives) with access rules set by the host.

### For fans

1. Open the host Legacy / Vault surfaces linked from the event or host page
2. Check the unlock rule (ticket holders, followers, purchase, etc.)
3. Unlock only through official Pàdéyá flows — never pay off-platform for “Vault access”

### For hosts

Publish Vault items from Vault Studio with clear access rules. Don’t overclaim exclusivity you can’t enforce.

::cta{label="Explore hosts"; href="/hosts"}
""",
    },
    {
        "title": "How ambassador campaigns work",
        "slug": "how-ambassador-campaigns-work",
        "category": "joining-campaigns",
        "tags": ["hosts", "fans", "how-to"],
        "content_type": "how_to",
        "difficulty": "intermediate",
        "audiences": ["ambassador", "host", "fan"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Ambassador campaigns | Pàdéyá Help",
        "seo_description": (
            "Join host campaigns, share tracked links or codes, and "
            "earn when eligible conversions complete."
        ),
        "excerpt": (
            "Hosts launch tracked campaigns. Ambassadors share approved "
            "links/codes and earn per campaign rules."
        ),
        "body": """## Ambassadors

Ambassador campaigns let hosts grow ticket sales with tracked referrals.

### For ambassadors

1. Open [Ambassadors](/ambassadors) and join eligible campaigns
2. Share only your tracked link or code
3. Check clicks/conversions in your campaign dashboard
4. Rewards follow the campaign’s published rules and payout timing

### For hosts

Launch campaigns from host tools, set commission rules carefully, and monitor for abuse.

::cta{label="Ambassadors"; href="/ambassadors"}
""",
    },
    {
        "title": "How sponsorship inquiries work",
        "slug": "how-sponsorship-inquiries-work",
        "category": "sending-sponsorship-inquiries",
        "tags": ["hosts", "how-to"],
        "content_type": "how_to",
        "difficulty": "intermediate",
        "audiences": ["sponsor", "host"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Sponsorship inquiries | Pàdéyá Help",
        "seo_description": (
            "Find hosts and events, send sponsorship inquiries, and "
            "manage requests in the sponsorship workspace."
        ),
        "excerpt": (
            "Browse hosts/events, send an inquiry with clear brand goals, "
            "and track status in sponsorship tools."
        ),
        "body": """## Sponsorships

Pàdéyá helps brands and hosts connect. Hosts remain responsible for delivering agreed on-site activations.

### For sponsors

1. Browse [Sponsors](/sponsors) overview and host/event pages
2. Send an inquiry with budget range, goals, and deliverables you need
3. Manage replies and status in your sponsorship requests

### For hosts

Respond clearly, set deliverables you can fulfill, and keep communications on-platform when possible.

::cta{label="Sponsors"; href="/sponsors"}
""",
    },
    {
        "title": "How Pàdéyá fees and host earnings work",
        "slug": "how-padeya-fees-and-host-earnings-work",
        "category": "platform-fees",
        "tags": ["hosts", "how-to"],
        "content_type": "faq",
        "difficulty": "intermediate",
        "audiences": ["host", "fan", "visitor"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Fees and host earnings | Pàdéyá Help",
        "seo_description": (
            "High-level overview of platform fees, payment processing, "
            "and where hosts review earnings."
        ),
        "excerpt": (
            "Checkout may include platform and processing fees. Hosts "
            "review earnings in the host finance surfaces."
        ),
        "body": """## Fees and earnings

Pàdéyá uses configurable platform fees for tickets, merch, Vault, and related products. Payment processing fees may also appear as a processing fee when configured.

### Key rules

- **Buyer platform fee is paid by the buyer.** It appears on checkout and is kept by Pàdéyá — it does not inflate host gross sales.
- **Host commission is deducted from host earnings.** Buyers do not see host commercial rates at checkout.
- **Fee settings can differ by host.** Some hosts may have custom overrides.
- **Order fee snapshots preserve the fee terms used at the time of sale.** Later admin changes do not rewrite past orders.

### For buyers

- Fee lines appear at checkout when configured (service / processing)
- The total you pay is calculated on the server; the payment amount must match that total
- Refunds of fees follow the [Refund Policy](/refund-policy) and host rules

### For hosts

1. Review [Pricing](/pricing) for the public fee explanation
2. Open **Host → Earnings** to see gross sales, Pàdéyá deductions, and net
3. Your own fee terms appear on the earnings page (never other hosts’ rates)
4. Request payouts from available balance; completion is admin-only with evidence

This guide does not invent live percentages — use Pricing, admin fee settings, and your host statements for current numbers.

::cta{label="Pricing"; href="/pricing"}
""",
    },
    {
        "title": "How payments work on Pàdéyá",
        "slug": "how-payments-work",
        "category": "secure-payments",
        "tags": ["tickets", "how-to", "fans"],
        "content_type": "faq",
        "difficulty": "beginner",
        "audiences": ["fan", "host", "visitor"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Secure payments | Pàdéyá Help",
        "seo_description": (
            "Payments are processed through supported providers. "
            "Tickets issue only after verified success."
        ),
        "excerpt": (
            "Complete hosted checkout with a supported method. Pending "
            "or failed payments do not issue tickets."
        ),
        "body": """## Payments

Pàdéyá uses supported payment providers for secure checkout. Never send money to personal accounts claiming to be Pàdéyá staff.

### What “pending” means

- The provider is still confirming the charge
- Tickets appear after verification — not on verbal confirmation
- If money left your bank but tickets didn’t appear, open [Support](/support) with the payment reference

### Safety

- Use official checkout only
- Keep receipts and references
- Report suspicious payment requests via [Report](/report)

::cta{label="Contact support"; href="/support"}
""",
    },
    {
        "title": "How to contact support",
        "slug": "how-to-contact-support",
        "category": "support-tickets",
        "tags": ["how-to", "getting-started"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "host", "visitor", "admin", "sponsor", "ambassador"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Contact Support | Pàdéyá Help",
        "seo_description": (
            "Search Help first, then open a tracked Support ticket with "
            "your topic and references."
        ),
        "excerpt": (
            "Try Help Center articles first. If you’re still stuck, open "
            "a Support ticket with clear details."
        ),
        "body": """## Get help efficiently

1. Search the [Help Center](/help)
2. Try self-service links (My Tickets, orders, host desk)
3. Open [Support](/support), pick a topic, and review suggestions
4. Only then choose **I still need help — open ticket**

### Include

- Topic category
- Order/ticket/event references
- What you already tried

Guests can open a ticket with email and track it with the ticket number.

::cta{label="Open Support"; href="/support"}
""",
    },
    {
        "title": "How to appeal a restriction or suspension",
        "slug": "how-to-appeal-restriction",
        "category": "suspensions-and-appeals",
        "tags": ["safety", "how-to"],
        "content_type": "how_to",
        "difficulty": "intermediate",
        "audiences": ["fan", "host", "ambassador", "sponsor", "visitor"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Appeal a restriction | Pàdéyá Help",
        "seo_description": (
            "If your account was restricted, submit an appeal with facts "
            "and references through the appeals flow or Support."
        ),
        "excerpt": (
            "Read the restriction notice, gather facts, and submit an "
            "appeal — don’t create duplicate accounts to bypass enforcement."
        ),
        "body": """## Restrictions and appeals

Pàdéyá may restrict accounts for safety, fraud, abuse, or policy risk. Appeals should stick to facts.

### Steps

1. Read the notice you received (email or in-product)
2. Collect order IDs, screenshots of relevant UI (not private keys), and a clear timeline
3. Submit an appeal through the account appeals flow when available, or open [Support](/support) under Account / login
4. Wait for a response — creating new accounts to bypass a restriction can make things worse

### Related

- [Community Guidelines](/community-guidelines)
- [Safety Center](/safety)
- [Report](/report)

::cta{label="Open Support"; href="/support"}
""",
    },
    {
        "title": "Login, sessions, and account security",
        "slug": "login-and-account-security",
        "category": "login-and-security",
        "tags": ["safety", "getting-started"],
        "content_type": "faq",
        "difficulty": "beginner",
        "audiences": ["fan", "host", "admin", "visitor"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Login and security | Pàdéyá Help",
        "seo_description": (
            "Keep your Pàdéyá account secure — passwords, sessions, "
            "and what to do if you suspect unauthorized access."
        ),
        "excerpt": (
            "Protect tickets, host tools, and payouts with strong "
            "sign-in hygiene."
        ),
        "body": """## Stay in control of your account

- Use a unique password for Pàdéyá
- Sign out of shared devices after desk shifts
- Never share one-time codes or payment references in public chats

### Suspected compromise

Change your password, review recent sessions in Settings, and open a [Support](/support) ticket if orders look wrong.

::cta{label="Account settings"; href="/dashboard/settings"}
""",
    },
    {
        "title": "Find events that match your vibe",
        "slug": "find-events-on-padeya",
        "category": "finding-events",
        "tags": ["fans", "getting-started"],
        "content_type": "text",
        "difficulty": "beginner",
        "audiences": ["fan", "visitor"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Find events on Pàdéyá | Help Center",
        "seo_description": (
            "Filter by city, vibe, and price. Follow hosts you trust and "
            "catch the next drop on Pàdéyá."
        ),
        "excerpt": (
            "Use filters, featured nights, and host follows to move from "
            "browse to ticket without leaving Pàdéyá."
        ),
        "body": """## Discovery with intent

1. Start on [Events](/events) — filter by city, weekend, and price
2. Open [Hosts](/hosts) when you already know who you trust
3. Follow hosts so the next drop is easier to catch

::cta{label="Explore events"; href="/events"}
""",
    },
    {
        "title": "Following hosts and leaving reviews",
        "slug": "following-hosts-and-reviews",
        "category": "following-hosts",
        "tags": ["fans", "how-to"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Follow hosts and reviews | Pàdéyá Help",
        "seo_description": (
            "Follow hosts you trust and leave honest reviews after nights "
            "you attended."
        ),
        "excerpt": (
            "Follow from host or event pages. Reviews should be truthful — "
            "hosts cannot delete fan reviews."
        ),
        "body": """## Follow and review

### Follow a host

Open the host Legacy page or event page and choose **Follow**.

### Reviews

After eligible attendance, leave an honest review. Hosts cannot delete reviews. Abuse of the review system can be reported.

::cta{label="Browse hosts"; href="/hosts"}
""",
    },
    {
        "title": "Messaging fans and hosts on Pàdéyá",
        "slug": "messaging-on-padeya",
        "category": "messages",
        "tags": ["fans", "hosts", "how-to", "safety"],
        "content_type": "how_to",
        "difficulty": "beginner",
        "audiences": ["fan", "host"],
        "featured": False,
        "featured_sort": 0,
        "video_url": None,
        "seo_title": "Messaging on Pàdéyá | Help Center",
        "seo_description": (
            "Fan↔host messaging follows product permissions. Report abuse "
            "and never share payment secrets in chat."
        ),
        "excerpt": (
            "Use Messages for fan↔host conversations. Block and report "
            "abuse; keep payments on official checkout."
        ),
        "body": """## Messaging rules

- Fan↔host threads follow product permission rules
- Don’t share passwords, OTPs, or off-platform payment instructions
- Use block/report tools when someone harasses you
- Emergencies: contact local authorities first

::cta{label="Open messages"; href="/dashboard/messages"}
""",
    },
]
