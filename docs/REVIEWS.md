# Reviews (Pàdéyá)

Public event and merch reviews build host trust and Fan Passport history. Hosts cannot delete public reviews; moderation is hide/restore (admin) or host reply where product allows.

Related: [LEGACY_PAGE.md](./LEGACY_PAGE.md) · [FAN_PASSPORT.md](./FAN_PASSPORT.md) · [MERCH.md](./MERCH.md) · [COMMERCE.md](./COMMERCE.md) · [HOST_AS_FAN.md](./HOST_AS_FAN.md)

## Core rules

- Reviews are eligibility-gated (e.g. verified attendance / paid merch purchase) on product surfaces.
- Public Passport and Legacy never reveal private/secret event attendance via review copy.
- Merch reviews: hosts cannot delete; admin may hide/restore; public list is allowlisted.

## Own-host public reviews (Host-as-Fan)

Hosts remain Personal/Fan users and may leave public reviews for **other** hosts normally.

The **host owner** cannot publicly review **their own** host workspace (event or merch):

- Guard: `assert_not_own_host_public_review` (`app/hosts/fan_self_abuse.py`)
- Detail: “You can’t publicly review your own host workspace.”
- Status: **403**
- Review prompts / eligibility for own host stay blocked for the owner

**Not blocked:** team/staff and other fans reviewing that host when eligible.

Owner self-reviews must not inflate Legacy / discover trust metrics.

Details: [HOST_AS_FAN.md](./HOST_AS_FAN.md).
