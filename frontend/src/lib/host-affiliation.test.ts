import { describe, expect, it } from "vitest";

import { isAffiliatedWithHost, ownedHostIds } from "./host-affiliation";

describe("isAffiliatedWithHost", () => {
  const workspaces = [
    {
      host_id: "host-a",
      slug: "lagos-nights",
      is_owner: true,
      kind: "owner" as const,
    },
    {
      host_id: "host-b",
      slug: "abuja-live",
      is_owner: true,
      kind: "owner" as const,
    },
  ];

  it("matches by host id for owned workspaces", () => {
    expect(
      isAffiliatedWithHost(workspaces, { hostId: "host-a" }),
    ).toBe(true);
    expect(
      isAffiliatedWithHost(workspaces, { hostId: "host-z" }),
    ).toBe(false);
  });

  it("matches by slug and ignores @", () => {
    expect(
      isAffiliatedWithHost(workspaces, { hostSlug: "@Lagos-Nights" }),
    ).toBe(true);
    expect(
      isAffiliatedWithHost(workspaces, { hostSlug: "other" }),
    ).toBe(false);
  });

  it("does not treat Host A ownership as Host B", () => {
    expect(
      isAffiliatedWithHost(
        [
          {
            host_id: "host-a",
            slug: "lagos-nights",
            is_owner: true,
            kind: "owner",
          },
        ],
        { hostId: "host-b", hostSlug: "abuja-live" },
      ),
    ).toBe(false);
  });

  it("ignores team and staff workspaces", () => {
    expect(
      isAffiliatedWithHost(
        [
          {
            host_id: "host-a",
            slug: "lagos-nights",
            is_owner: false,
            kind: "team_member",
          },
          {
            host_id: "host-a",
            slug: "lagos-nights",
            is_owner: false,
            kind: "event_staff",
          },
        ],
        { hostId: "host-a" },
      ),
    ).toBe(false);
  });
});

describe("ownedHostIds", () => {
  it("returns only owner host ids", () => {
    expect(
      ownedHostIds([
        {
          host_id: "host-a",
          is_owner: true,
          kind: "owner",
        },
        {
          host_id: "host-b",
          is_owner: false,
          kind: "team_member",
        },
        {
          host_id: "host-c",
          is_owner: false,
          kind: "event_staff",
        },
      ]),
    ).toEqual(["host-a"]);
  });
});
