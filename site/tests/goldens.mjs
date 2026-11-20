// The HTML the shared renderers write for every page of tests/bundle, kept in tests/goldens/ so
// a change to the markup shows as a change to these files (openspec pairs-site, shared
// components): a refactor of the renderers leaves them byte for byte the same, and a change
// meant to show is reviewed in their diff. `UPDATE_GOLDENS=1 node --test tests/goldens.test.mjs`
// writes them again from the renderers.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readBundle } from "../src/lib/bundle.ts";
import { narrowerPairs, pairView } from "../src/lib/pair-view.ts";
import { renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
import { categoryListing, interventionListing, topicListing } from "../src/lib/listing-view.ts";
import { renderListingBand, renderListingSheet } from "../src/lib/listing-render.ts";
import { renderEmbedArticle, renderEmbedRegistries } from "../src/lib/embed-render.ts";
import { SITE } from "../site.config.mjs";

export const GOLDENS = fileURLToPath(new URL("./goldens", import.meta.url));
const BUNDLE = fileURLToPath(new URL("./bundle", import.meta.url));
// A MeSH year for the category pages' credit; the fixture's manifest states none.
const MESH_EDITION = "2026";

/** Every page's HTML as the renderers write it, by its file under tests/goldens/. */
export function renderedGoldens() {
  const files = readBundle(BUNDLE).pages;
  const pairs = files.PairPage;
  const published = new Set(Object.keys(pairs));
  const categories = new Set(Object.keys(files.PairClinicalCategoryPage));
  const out = new Map();
  for (const [address, file] of Object.entries(pairs)) {
    const view = pairView(file);
    const narrower = narrowerPairs(file, files.PairInterventionPage[file.row.intervention.slug] ?? null, published);
    out.set(`pairs/${address}.html`, `${renderPairBand(view)}\n${renderPairSheet(view, narrower)}\n`);
    out.set(`embeds/${address}.html`, `${renderEmbedArticle(view, SITE.name, SITE.url)}\n${renderEmbedRegistries(view)}\n`);
  }
  const listings = [
    ...Object.entries(files.PairInterventionPage).map(([key, file]) => [`intervention-${key}`, interventionListing(file, published)]),
    ...Object.entries(files.PairClinicalCategoryPage).map(([key, file]) => [`clinical-${key}`, categoryListing(file, published, categories)]),
    ...Object.entries(files.PairTopicPage).map(([key, file]) => [`topic-${key}`, topicListing(file, published)]),
  ];
  for (const [name, view] of listings) out.set(`listings/${name}.html`, `${renderListingBand(view)}\n${renderListingSheet(view, MESH_EDITION)}\n`);
  return out;
}

/** The goldens on disk, by the same names. */
export function keptGoldens(folder = GOLDENS, { within = null } = {}) {
  const out = new Map();
  if (!fs.existsSync(folder)) return out;
  for (const name of fs.readdirSync(folder, { recursive: true })) {
    if (within && !within(name)) continue;
    const file = path.join(folder, name);
    if (fs.statSync(file).isFile() && name.endsWith(".html")) out.set(name.split(path.sep).join("/"), fs.readFileSync(file, "utf8"));
  }
  return out;
}

/** Writes the given goldens, removing any file that no longer has one. */
export function writeGoldens(goldens, folder = GOLDENS, within = null) {
  for (const name of keptGoldens(folder, { within }).keys()) if (!goldens.has(name)) fs.rmSync(path.join(folder, name));
  for (const [name, html] of goldens) {
    fs.mkdirSync(path.dirname(path.join(folder, name)), { recursive: true });
    fs.writeFileSync(path.join(folder, name), html);
  }
}
