// @ts-check
import { defineConfig } from "astro/config";

import { EXTENSION_OFFERED, SITE } from "./site.config.mjs";

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

// The pair pages (openspec pairs-site) are built only from a bundle of the lab's page
// files named in PAIRS_BUNDLE. Until the cutover a build without one is the claims site
// alone, so publishing from main adds no pair page.
const pairPages = {
  name: "pair-pages",
  hooks: {
    /** @param {{ injectRoute: (route: { pattern: string, entrypoint: string }) => void }} setup */
    "astro:config:setup": ({ injectRoute }) => {
      if (process.env.PAIRS_BUNDLE) {
        injectRoute({ pattern: "/[address]", entrypoint: "./src/pair/PairRoute.astro" });
      }
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
