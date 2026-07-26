import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  apiRequest: vi.fn(),
}));

import { apiRequest } from "@/lib/api";
import {
  fetchPublicMaintenanceStatus,
  resetPublicMaintenanceStatusCache,
} from "./maintenance-public";

const mockedApi = vi.mocked(apiRequest);

describe("fetchPublicMaintenanceStatus single-flight", () => {
  beforeEach(() => {
    resetPublicMaintenanceStatusCache();
    mockedApi.mockReset();
  });

  it("dedupes concurrent callers to one network request", async () => {
    let resolveRequest!: (value: { mode: string; maintenance: boolean; title: string; message: string }) => void;
    mockedApi.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }) as ReturnType<typeof apiRequest>,
    );

    const a = fetchPublicMaintenanceStatus();
    const b = fetchPublicMaintenanceStatus();
    expect(mockedApi).toHaveBeenCalledTimes(1);

    resolveRequest!({
      mode: "off",
      maintenance: false,
      title: "",
      message: "",
    });
    await expect(Promise.all([a, b])).resolves.toEqual([
      expect.objectContaining({ mode: "off" }),
      expect.objectContaining({ mode: "off" }),
    ]);
  });

  it("serves a short TTL cache for follow-up callers", async () => {
    mockedApi.mockResolvedValue({
      mode: "off",
      maintenance: false,
      title: "",
      message: "",
    });
    await fetchPublicMaintenanceStatus();
    await fetchPublicMaintenanceStatus();
    expect(mockedApi).toHaveBeenCalledTimes(1);
  });
});
