import { describe, expect, it } from "vitest";

import { optimizeInlineImages } from "@/lib/inline-images";

const CLD = "https://res.cloudinary.com/demo/image/upload/v123/posts/inline/x.jpg";

describe("optimizeInlineImages", () => {
  it("injects f_auto,q_auto + width into the src of a Cloudinary image", () => {
    const out = optimizeInlineImages(`<img src="${CLD}">`);
    expect(out).toContain(
      'src="https://res.cloudinary.com/demo/image/upload/f_auto,q_auto,w_1200/v123/posts/inline/x.jpg"',
    );
  });

  it("adds a width srcset and sizes", () => {
    const out = optimizeInlineImages(`<img src="${CLD}">`);
    expect(out).toContain("srcset=");
    expect(out).toContain("f_auto,q_auto,w_400/");
    expect(out).toContain("f_auto,q_auto,w_1600/");
    expect(out).toContain("400w");
    expect(out).toContain("1600w");
    expect(out).toContain('sizes="(min-width: 768px) 720px, 100vw"');
  });

  it("adds lazy loading and async decoding", () => {
    const out = optimizeInlineImages(`<img src="${CLD}">`);
    expect(out).toContain('loading="lazy"');
    expect(out).toContain('decoding="async"');
  });

  it("preserves existing alt text", () => {
    const out = optimizeInlineImages(`<img src="${CLD}" alt="A diagram">`);
    expect(out).toContain('alt="A diagram"');
  });

  it("does not duplicate attributes the editor already set", () => {
    const out = optimizeInlineImages(`<img src="${CLD}" loading="eager">`);
    expect(out).toContain('loading="eager"');
    expect(out.match(/loading=/g)).toHaveLength(1);
  });

  it("leaves non-Cloudinary images untouched", () => {
    const html = '<img src="https://example.com/photo.jpg" alt="x">';
    expect(optimizeInlineImages(html)).toBe(html);
  });

  it("works for images wrapped in a figure", () => {
    const out = optimizeInlineImages(`<figure><img src="${CLD}"></figure>`);
    expect(out).toContain("<figure>");
    expect(out).toContain("</figure>");
    expect(out).toContain("f_auto,q_auto,w_1200/");
  });

  it("handles a self-closing img tag without leaving a stray slash", () => {
    const out = optimizeInlineImages(`<img src="${CLD}" />`);
    expect(out).not.toContain("/ ");
    expect(out).not.toContain(" />");
    expect(out).toContain("f_auto,q_auto");
  });

  it("leaves non-image markup alone", () => {
    const html = "<p>Text</p><h2>Heading</h2>";
    expect(optimizeInlineImages(html)).toBe(html);
  });
});
