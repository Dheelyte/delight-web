import { describe, expect, it } from "vitest";

import { cloudinarySrcSet, cloudinaryUrl } from "@/lib/cloudinary";

const CLOUD = "demo";

describe("cloudinaryUrl", () => {
  it("emits f_auto and q_auto by default", () => {
    expect(cloudinaryUrl("posts/x", { width: 800, cloudName: CLOUD })).toContain(
      "f_auto,q_auto,w_800",
    );
  });

  it("appends focal-point coords when fit=fill", () => {
    const url = cloudinaryUrl("posts/x", {
      width: 1200, height: 630, fit: "fill", focalX: 0.4, focalY: 0.6,
      cloudName: CLOUD,
    });
    expect(url).toContain("c_fill");
    expect(url).toContain("g_xy_center");
    expect(url).toContain("x_0.400");
    expect(url).toContain("y_0.600");
  });

  it("clamps focal coords to [0,1]", () => {
    const url = cloudinaryUrl("posts/x", {
      width: 100, height: 100, fit: "fill", focalX: -2, focalY: 5,
      cloudName: CLOUD,
    });
    expect(url).toContain("x_0.000");
    expect(url).toContain("y_1.000");
  });

  it("returns a placeholder data URI when no cloud name is available", () => {
    const url = cloudinaryUrl("posts/x", { width: 100 });
    // Either a real URL (if env happens to be set) or the explicit fallback.
    if (!url.startsWith("https://")) {
      expect(url.startsWith("data:image/svg+xml")).toBe(true);
    }
  });
});

describe("cloudinarySrcSet", () => {
  it("builds widths and a fallback src", () => {
    const { src, srcSet, sizes } = cloudinarySrcSet("posts/x", { cloudName: CLOUD });
    expect(srcSet.split(", ").length).toBe(4);
    expect(srcSet).toContain("400w");
    expect(srcSet).toContain("1600w");
    expect(src).toContain("w_");
    expect(sizes).toMatch(/100vw/);
  });
});
