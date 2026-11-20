// @ts-check
import { defineConfig } from "astro/config";

import { EXTENSION_OFFERED, SITE } from "./site.config.mjs";
import { writeBundleCode } from "./scripts/bundle-code.mjs";

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
    "astro:config:setup": async ({ injectRoute }) => {
      if (process.env.PAIRS_BUNDLE) {
        // The validators and types of the bundle's page models (decision 1), for the Worker.
        await writeBundleCode(process.env.PAIRS_BUNDLE, ".bundle-code");
        injectRoute({ pattern: "/[address]", entrypoint: "./src/pair/PairRoute.astro" });
        injectRoute({ pattern: "/intervention/[intervention]", entrypoint: "./src/pair/InterventionRoute.astro" });
        injectRoute({ pattern: "/condition/[condition]", entrypoint: "./src/pair/ConditionRoute.astro" });
        // A topic's and a clinical category's page list pairs in a build that reads a
        // bundle; the claim versions of these two routes then make no page.
        injectRoute({ pattern: "/topic/[topic]", entrypoint: "./src/pair/TopicRoute.astro" });
        injectRoute({ pattern: "/clinical/[category]", entrypoint: "./src/pair/CategoryRoute.astro" });
        injectRoute({ pattern: "/data/pairs/[address].json", entrypoint: "./src/pair/pair-record.json.ts" });
        injectRoute({ pattern: "/data/pairs.json", entrypoint: "./src/pair/pairs-index.json.ts" });
        injectRoute({ pattern: "/og/[address].png", entrypoint: "./src/pair/card-wide.png.ts" });
        injectRoute({ pattern: "/og/square/[address].png", entrypoint: "./src/pair/card-square.png.ts" });
        injectRoute({ pattern: "/og/tall/[address].png", entrypoint: "./src/pair/card-tall.png.ts" });
        injectRoute({ pattern: "/embed/[address]", entrypoint: "./src/pair/EmbedRoute.astro" });
        injectRoute({ pattern: "/oembed/[address].json", entrypoint: "./src/pair/oembed.json.ts" });
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
