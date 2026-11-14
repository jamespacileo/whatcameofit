// How pages are found and cited: each page's canonical address, and the structured data
// pages carry for search engines. The data names pages, dates, the site, its publisher,
// the trail of pages above each one and the open dataset, and describes without rating:
// fact-check, review and rating types each state a verdict, so ClaimReview, Review and
// Rating are never used.
import { SITE } from "../../site.config.mjs";
import type { ExportedClaim } from "./export";

/** A page's address on the public site, written as the site links it: no trailing slash. */
export function canonicalAddress(pathname: string): string {
  const path = pathname.replace(/(\/index)?\.html$/, "").replace(/\/+$/, "");
  return new URL(path || "/", SITE.url).href;
}

/** One object of structured data, as written into a page. */
export type Structured = Record<string, unknown>;

const SITE_ID = `${canonicalAddress("/")}#site`;
const PUBLISHER_ID = `${canonicalAddress("/")}#publisher`;
const GUIDE_ID = `${canonicalAddress("/guide")}#terms`;

/** The publisher, with the mark as its logo. */
function publisher(): Structured {
  return {
    "@type": "Organization",
    "@id": PUBLISHER_ID,
    name: SITE.name,
    url: canonicalAddress("/"),
    logo: { "@type": "ImageObject", url: canonicalAddress("/icon-512.png"), width: 512, height: 512 },
  };
}

/** The home page's data: the site itself and who publishes it. */
export function siteData(): Structured[] {
  return [
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "@id": SITE_ID,
      name: SITE.name,
      description: SITE.description,
      url: canonicalAddress("/"),
      inLanguage: "en-GB",
      publisher: { "@id": PUBLISHER_ID },
    },
    { "@context": "https://schema.org", ...publisher() },
  ];
}

/** A step in the trail of pages above a page: its name and its path on the site. */
export interface Crumb {
  name: string;
  path: string;
}

/** The trail from the home page down to this one, the home page first. */
export function breadcrumbData(trail: Crumb[]): Structured {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [{ name: SITE.name, path: "/" }, ...trail].map((crumb, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: crumb.name,
      item: canonicalAddress(crumb.path),
    })),
  };
}

export function claimPageData(
  claim: ExportedClaim,
  lastCheckedAt: string | null,
  description?: string,
): Structured {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: claim.headline,
    url: canonicalAddress(`/${claim.slug}`),
    ...(description ? { description } : {}),
    inLanguage: "en-GB",
    image: canonicalAddress(`/og/${claim.slug}.png`),
    ...(claim.first_reported_date ? { datePublished: claim.first_reported_date } : {}),
    ...(lastCheckedAt ? { dateModified: lastCheckedAt } : {}),
    isPartOf: { "@type": "WebSite", "@id": SITE_ID, name: SITE.name, url: canonicalAddress("/") },
    publisher: publisher(),
  };
}

/** The open data file, described for dataset search. */
export function datasetData(options: {
  description: string;
  licence: string;
  claimCount: number;
  dateModified: string;
}): Structured {
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: `${SITE.name} claims`,
    description: options.description,
    url: canonicalAddress("/data"),
    license: options.licence,
    isAccessibleForFree: true,
    inLanguage: "en-GB",
    dateModified: options.dateModified,
    creator: publisher(),
    size: `${options.claimCount} claims`,
    distribution: {
      "@type": "DataDownload",
      encodingFormat: "application/json",
      contentUrl: canonicalAddress("/data/claims.json"),
    },
  };
}

/** A guide entry as a defined term: the word, its one-sentence answer and the set it belongs to. */
export function definedTermData(entry: { slug: string; title: string; answer: string }): Structured {
  return {
    "@context": "https://schema.org",
    "@type": "DefinedTerm",
    "@id": canonicalAddress(`/guide/${entry.slug}`),
    name: entry.title,
    description: entry.answer,
    url: canonicalAddress(`/guide/${entry.slug}`),
    inLanguage: "en-GB",
    inDefinedTermSet: { "@type": "DefinedTermSet", "@id": GUIDE_ID, name: `${SITE.name} guide` },
  };
}

/** The guide as a set of defined terms, each named with its address. */
export function guideData(
  description: string,
  entries: readonly { slug: string; title: string }[],
): Structured {
  return {
    "@context": "https://schema.org",
    "@type": "DefinedTermSet",
    "@id": GUIDE_ID,
    name: `${SITE.name} guide`,
    description,
    url: canonicalAddress("/guide"),
    inLanguage: "en-GB",
    publisher: { "@id": PUBLISHER_ID },
    hasDefinedTerm: entries.map((entry) => ({
      "@type": "DefinedTerm",
      "@id": canonicalAddress(`/guide/${entry.slug}`),
      name: entry.title,
      url: canonicalAddress(`/guide/${entry.slug}`),
    })),
  };
}
