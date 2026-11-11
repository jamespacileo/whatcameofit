// @ts-check
import { defineConfig } from "astro/config";

import { SITE } from "./site.config.mjs";

// One address for everything absolute; see site.config.mjs.
export default defineConfig({
  site: SITE.url,
  trailingSlash: "ignore",
});
