import { describe, it, expect, beforeEach, vi } from "vitest";

import {
  clearCreationResult,
  clearPendingTemplate,
  newCreationKey,
  readCreationResult,
  readPendingTemplate,
  writeCreationResult,
  writePendingTemplate,
} from "./blog-creation";

function mockSessionStorage() {
  const store = new Map<string, string>();
  const storage = {
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  };
  vi.stubGlobal("sessionStorage", storage);
  return storage;
}

describe("blog-creation helpers", () => {
  beforeEach(() => {
    mockSessionStorage();
    vi.restoreAllMocks();
  });

  it("newCreationKey returns a non-empty string", () => {
    expect(newCreationKey()).toMatch(
      /^[0-9a-f-]{36}$|creation-\d+-[a-z0-9]+$/i,
    );
  });

  it("persists and reads creation results by key", () => {
    const key = newCreationKey();
    expect(readCreationResult(key)).toBeNull();
    writeCreationResult(key, "post-123");
    expect(readCreationResult(key)).toBe("post-123");
    clearCreationResult(key);
    expect(readCreationResult(key)).toBeNull();
  });

  it("persists pending template application for recovery", () => {
    const pending = {
      postId: "post-abc",
      templateSlug: "article",
      tab: "write" as const,
      creationKey: "key-1",
      createdAt: new Date().toISOString(),
    };
    writePendingTemplate(pending);
    expect(readPendingTemplate()).toEqual(pending);
    clearPendingTemplate();
    expect(readPendingTemplate()).toBeNull();
  });

  it("returns null when sessionStorage is unavailable", () => {
    vi.stubGlobal("sessionStorage", {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => {
        throw new Error("blocked");
      },
    });
    expect(readCreationResult("x")).toBeNull();
    expect(readPendingTemplate()).toBeNull();
  });
});
