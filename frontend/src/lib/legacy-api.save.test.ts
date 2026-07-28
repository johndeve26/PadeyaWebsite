import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

vi.mock("@/lib/api-base", () => ({
  getApiBaseUrl: () => "https://padeyawebsite.onrender.com",
  getApiPrefix: () => "/api/v1",
}));

vi.mock("@/lib/auth/storage", () => ({
  getAccessToken: () => "test-token",
  getRefreshToken: () => null,
  isImpersonationSession: () => false,
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}));

describe("legacy profile save API", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock as typeof fetch;
  });

  it("PATCHes the public host legacy endpoint with auth", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        host_id: "00000000-0000-0000-0000-000000000001",
        display_name: "Padeya",
        username: "padeya",
        status: "active",
        verified: true,
        legacy_status: "active",
        profile: null,
        stats: {
          events_hosted: 0,
          tickets_sold: 0,
          verified_checkins: 0,
          average_verified_rating: null,
          review_count: 0,
          followers: 0,
          repeat_buyers_rate: null,
          refund_dispute_rate: null,
          legacy_status: "active",
        },
        about: null,
        upcoming_events: [],
        past_events: [],
        reviews: [],
        follow_enabled: true,
        share_path: "/@padeya",
      }),
    });

    const { updateMyLegacyProfile } = await import("@/lib/legacy-api");
    await updateMyLegacyProfile({
      display_name: "Padeya",
      username: "Padeya",
      contact: {
        preference: "none",
        show_contact_form: false,
      },
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://padeyawebsite.onrender.com/api/v1/host/legacy");
    expect(init.method).toBe("PATCH");
    expect(init.headers).toMatchObject({
      Authorization: "Bearer test-token",
      "Content-Type": "application/json",
    });
    expect(JSON.parse(String(init.body))).toMatchObject({
      display_name: "Padeya",
      username: "Padeya",
      contact: { preference: "none", show_contact_form: false },
    });
  });
});
