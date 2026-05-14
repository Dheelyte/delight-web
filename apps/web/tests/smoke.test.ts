import { describe, it, expect } from "vitest";
import { cn } from "@/lib/cn";

describe("cn helper", () => {
  it("merges tailwind classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("handles conditional classes", () => {
    expect(cn("a", false && "b", "c")).toBe("a c");
  });
});
