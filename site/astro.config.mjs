// @ts-check
import { defineConfig } from "astro/config";

import { EXTENSION_OFFERED, SITE } from "./site.config.mjs";
import { writeBundleCode } from "./scripts/bundle-code.mjs";
import { rendererDigest } from "./scripts/renderer-digest.mjs";

// The extension page exists only once a store lists the extension. A page that
// offered nothing to install would be a dead end, so its route is added here, and
// only then; see site.config.mjs.
const extensionPage = {
  name: "extension-page",
  hooks: {
    /** @param {{ injectRoute: (route: { pattern: string, entrypoint: string }) => void }} setup */
    "astro:config:setup": ({ injectRoute }) => {
      if (EXTENSION_OFFERED) {
        injectRoute({ pattern: "/extension", entrypoint: "./src/landing/extension.astro" });
      }
    },
  },
};

// The pair pages (openspec pairs-site). The bundle of the lab's page files named in
// PAIRS_BUNDLE is the build's only input, so a build without one stops here.
const pairPages = {
  name: "pair-pages",
  hooks: {
    /** @param {{ injectRoute: (route: { pattern: string, entrypoint: string }) => void }} setup */
    "astro:config:setup": async ({ injectRoute }) => {
      if (!process.env.PAIRS_BUNDLE) {
        throw new Error("No bundle to build from: set PAIRS_BUNDLE to a folder of the lab's page files (tests/bundle is the small one the tests build).");
      }
      // The validators and types of the bundle's page models (decision 1), for the Worker.
      await writeBundleCode(process.env.PAIRS_BUNDLE, ".bundle-code");
      // The digest of the code that writes pages made on request, for the frames to carry
      // (scripts/renderer-digest.mjs): every entity tag takes it in.
      process.env.PAIRS_RENDERER_DIGEST = rendererDigest();
      // No file is built per pair (openspec pairs-site task 4.6): every pair's page, open data
      // record, embed, oEmbed description and card address is the Worker's, made on request
      // from D1 (worker/pairs.mjs, worker/shares.mjs), so the build's file count does not grow
      // with the pairs. The two frames it fills are built, and never served themselves.
      injectRoute({ pattern: "/pair-shell", entrypoint: "./src/pair/PairShell.astro" });
      injectRoute({ pattern: "/embed-shell", entrypoint: "./src/pair/EmbedShell.astro" });
      injectRoute({ pattern: "/condition/[condition]", entrypoint: "./src/pair/ConditionRoute.astro" });
      // An intervention's, a topic's and a clinical category's page are the Worker's, made on
      // request from the lab's page files (worker/listings.mjs).
      injectRoute({ pattern: "/data/pairs.json", entrypoint: "./src/pair/pairs-index.json.ts" });
    },
  },
};

// One address for everything absolute; see site.config.mjs.
export default defineConfig({
  site: SITE.url,
  trailingSlash: "ignore",
  integrations: [extensionPage, pairPages],
  // A page a reader points at is fetched before they press, so it opens at once.
  prefetch: { prefetchAll: true, defaultStrategy: "hover" },
});
