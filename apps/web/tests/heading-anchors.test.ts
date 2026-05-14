import { describe, expect, it } from "vitest";

import { addHeadingAnchors } from "@/lib/heading-anchors";

describe("addHeadingAnchors", () => {
  it("adds an id and wraps the heading in a self-link", () => {
    const { html } = addHeadingAnchors("<h2>This Is a Section</h2>");
    expect(html).toBe(
      '<h2 id="this-is-a-section">' +
        '<a class="heading-anchor" href="#this-is-a-section">This Is a Section</a>' +
        "</h2>",
    );
  });

  it("handles h3 as well as h2", () => {
    const { html } = addHeadingAnchors("<h3>Sub Section</h3>");
    expect(html).toContain('<h3 id="sub-section">');
    expect(html).toContain('href="#sub-section"');
  });

  it("derives the slug from text content, keeping inline markup in the link", () => {
    const { html } = addHeadingAnchors("<h2>A <strong>bold</strong> idea</h2>");
    expect(html).toContain('id="a-bold-idea"');
    // inline markup is preserved inside the anchor
    expect(html).toContain("<strong>bold</strong>");
  });

  it("disambiguates duplicate slugs with a numeric suffix", () => {
    const { html } = addHeadingAnchors(
      "<h2>Notes</h2><h2>Notes</h2><h2>Notes</h2>",
    );
    expect(html).toContain('id="notes"');
    expect(html).toContain('id="notes-2"');
    expect(html).toContain('id="notes-3"');
  });

  it("does not leak entity names into the slug", () => {
    // The classic bug: `&nbsp;` is six literal chars in a raw HTML string,
    // and n/b/s/p are alphanumeric — they must not survive into the slug.
    expect(addHeadingAnchors("<h2>My Section&nbsp;</h2>").html).toContain(
      'id="my-section"',
    );
    expect(addHeadingAnchors("<h2>Cats &amp; Dogs</h2>").html).toContain(
      'id="cats-dogs"',
    );
    expect(addHeadingAnchors("<h2>Notes &mdash; final</h2>").html).toContain(
      'id="notes-final"',
    );
  });

  it("decodes numeric entities before slugifying", () => {
    // &#233; is é → NFKD strips the accent → "e"
    expect(addHeadingAnchors("<h2>Caf&#233;</h2>").html).toContain('id="cafe"');
    // &#39; is an apostrophe → dropped
    expect(addHeadingAnchors("<h2>It&#39;s here</h2>").html).toContain(
      'id="it-s-here"',
    );
  });

  it("leaves non-heading content untouched", () => {
    const html = "<p>Para</p><ul><li>item</li></ul>";
    const result = addHeadingAnchors(html);
    expect(result.html).toBe(html);
    expect(result.headings).toEqual([]);
  });

  it("falls back to 'section' for headings with no slug-able text", () => {
    const { html } = addHeadingAnchors("<h2>—</h2>");
    expect(html).toContain('id="section"');
  });

  it("tolerates (and drops) attributes on the heading tag", () => {
    const { html } = addHeadingAnchors('<h2 class="x">Title</h2>');
    expect(html).toBe(
      '<h2 id="title">' +
        '<a class="heading-anchor" href="#title">Title</a>' +
        "</h2>",
    );
  });

  it("returns an ordered heading list for the table of contents", () => {
    const { headings } = addHeadingAnchors(
      "<h2>Intro</h2><p>x</p><h3>Detail &amp; nuance</h3><h2>Wrap Up</h2>",
    );
    expect(headings).toEqual([
      { level: 2, text: "Intro", slug: "intro" },
      { level: 3, text: "Detail & nuance", slug: "detail-nuance" },
      { level: 2, text: "Wrap Up", slug: "wrap-up" },
    ]);
  });
});
