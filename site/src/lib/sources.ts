// A page per article or post the site tracks, at /source/{outlet}-{title}: what it
// reported, and the claim or claims it reports. Built from the articles the export
// already carries; never shows any text from the article. Openspec auto-publish,
// source-pages "A page per source".
import type { ExportedClaim } from "./export.ts";

export interface Source {
  slug: string;
  url: string;
  outlet: string;
  title: string;
  published_date: string;
  claims: ExportedClaim[];
}

const MAX_SLUG = 70;

/** Lower case words joined by hyphens: the same rule as claim slugs. */
export function slugify(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function baseSlug(outlet: string, title: string): string {
  const joined = `${slugify(outlet)}-${slugify(title)}`.replace(/^-+|-+$/g, "");
  if (joined.length <= MAX_SLUG) return joined || "report";
  return joined.slice(0, MAX_SLUG).replace(/-[^-]*$/, "") || "report";
}

/**
 * Every tracked article once, with every claim that cites it. Slugs are made in the
 * order of the articles' addresses, so a build gives each article the same slug as the
 * last unless a new article with the same outlet and title arrives before it.
 */
export function sourcesOf(claims: ExportedClaim[]): Source[] {
  const byUrl = new Map<string, Source>();
  for (const claim of claims) {
    for (const article of claim.articles) {
      const known = byUrl.get(article.url);
      if (known) {
        if (!known.claims.includes(claim)) known.claims.push(claim);
        continue;
      }
      byUrl.set(article.url, {
        slug: "",
        url: article.url,
        outlet: article.outlet,
        title: article.title,
        published_date: article.published_date,
        claims: [claim],
      });
    }
  }
  const sources = [...byUrl.values()].sort((a, b) => (a.url < b.url ? -1 : a.url > b.url ? 1 : 0));
  const taken = new Set<string>();
  for (const source of sources) {
    const base = baseSlug(source.outlet, source.title);
    let slug = base;
    for (let number = 2; taken.has(slug); number += 1) slug = `${base}-${number}`;
    taken.add(slug);
    source.slug = slug;
  }
  return sources;
}
