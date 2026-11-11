// @ts-check
import { defineConfig } from "astro/config";

// The public address is undecided; link previews need an absolute one.
export default defineConfig({
  site: process.env.SITE_URL ?? "http://localhost:4321",
  trailingSlash: "ignore",
});
