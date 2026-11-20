// The built sitemap as a crawler reads it: the index at /sitemap.xml, then each file it names.
import fs from "node:fs";
import path from "node:path";

const locations = (text) => [...text.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1]);

/** The text of every sitemap file the index names, joined. */
export function sitemapText(dist) {
  const index = fs.readFileSync(path.join(dist, "sitemap.xml"), "utf8");
  return locations(index)
    .map((address) => fs.readFileSync(path.join(dist, new URL(address).pathname.slice(1)), "utf8"))
    .join("\n");
}

/** Every address the sitemap's files list. */
export function sitemapAddresses(dist) {
  return locations(sitemapText(dist));
}
