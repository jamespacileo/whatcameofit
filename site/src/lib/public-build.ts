// A public build must carry the public address: canonical addresses, structured data
// and the sitemap are all built from it, and a sitemap of local addresses must never
// ship. A build is public when PUBLIC_BUILD=1 is set and the export is not a preview.
// The check runs once, when this module is first imported.
import { LOCAL_HOST } from "../../scripts/deploy-checks.mjs";
import { SITE } from "../../site.config.mjs";
import { data } from "./export";

function isLocalAddress(address: string): boolean {
  return LOCAL_HOST.test(new URL(address).hostname);
}

if (process.env.PUBLIC_BUILD === "1" && !data.preview && isLocalAddress(SITE.url)) {
  throw new Error(
    `This is a public build (PUBLIC_BUILD=1), but the site's address is ${SITE.url}, a local one. The public address must be set as SITE.url in site/site.config.mjs before a public build.`,
  );
}
