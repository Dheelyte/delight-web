import { describe, expect, it } from "vitest";

import { safeNextPath } from "@/lib/safe-next";

describe("safeNextPath", () => {
  it("allows /admin paths", () => {
    expect(safeNextPath("/admin")).toBe("/admin");
    expect(safeNextPath("/admin/posts")).toBe("/admin/posts");
  });

  it("falls back for non-admin paths", () => {
    expect(safeNextPath("/")).toBe("/admin");
    expect(safeNextPath("/foo")).toBe("/admin");
  });

  it("blocks open-redirect attempts", () => {
    expect(safeNextPath("//evil.com")).toBe("/admin");
    expect(safeNextPath("/admin\\evil")).toBe("/admin");
    expect(safeNextPath("https://evil.com")).toBe("/admin");
  });

  it("handles missing input", () => {
    expect(safeNextPath(null)).toBe("/admin");
    expect(safeNextPath(undefined)).toBe("/admin");
    expect(safeNextPath("")).toBe("/admin");
  });

  it("blocks CRLF", () => {
    expect(safeNextPath("/admin\nfoo")).toBe("/admin");
  });
});
