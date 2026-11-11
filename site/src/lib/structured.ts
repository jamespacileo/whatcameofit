// How pages are found and cited: each page's canonical address, and the structured data
// a claim page carries for search engines. The data names the page, the date the claim
// was first reported, the date the registries were last checked and the site as
// publisher, and describes without rating: fact-check, review and rating types each
// state a verdict, so ClaimReview, Review and Rating are never used.
import { SITE } from "../../site.config.mjs";
import type { ExportedClaim } from "./export";

/** A page's address on the public site, written as the site links it: no trailing slash. */
export function canonicalAddress(pathname: string): string {
  const path = pathname.replace(/(\/index)?\.html$/, "").replace(/\/+$/, "");
  return new URL(path || "/", SITE.url).href;
}

export function claimPageData(claim: ExportedClaim, lastCheckedAt: string | null) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: claim.headline,
    url: canonicalAddress(`/${claim.slug}`),
    ...(claim.first_reported_date ? { datePublished: claim.first_reported_date } : {}),
    ...(lastCheckedAt ? { dateModified: lastCheckedAt } : {}),
    publisher: { "@type": "Organization", name: SITE.name, url: canonicalAddress("/") },
  };
}
