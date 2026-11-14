// The guide's entry files, read when the site is built: one Markdown file per entry in
// src/guide, named for its address. A build stops here when the files fail a check
// (see guide.ts), so no page of the guide is published from a set that is incomplete.
import type { AstroComponentFactory } from "astro/runtime/server/index.js";
import { assertGuide, orderedEntries, readEntry, type GuideEntry } from "./guide";

interface EntryFile {
  frontmatter: Record<string, unknown>;
  rawContent: () => string;
  Content: AstroComponentFactory;
}

const files = import.meta.glob<EntryFile>("../guide/*.md", { eager: true });

const read = Object.entries(files).map(([file, module]) => {
  const slug = file.split("/").pop()!.replace(/\.md$/, "");
  return { entry: readEntry(slug, module.frontmatter, module.rawContent()), Content: module.Content };
});

assertGuide(read.map(({ entry }) => entry));

/** Every entry, in the order the index lists them. */
export const guide: GuideEntry[] = orderedEntries(read.map(({ entry }) => entry));

const bodies = new Map(read.map(({ entry, Content }) => [entry.slug, Content]));

/** An entry's own text, as a component to draw. */
export const entryBody = (slug: string) => bodies.get(slug)!;

/** An entry by its address. */
export const entryAt = (slug: string) => guide.find((entry) => entry.slug === slug) ?? null;
