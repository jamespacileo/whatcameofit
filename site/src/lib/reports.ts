// News reports across all claims, for lists that are not about one claim.
import type { ExportedClaim } from "./export";

export interface Report {
  claim: ExportedClaim;
  outlet: string;
  title: string;
  url: string;
  publishedDate: string;
}

/** The newest reports first. Reports from the same day keep the order of their titles. */
export function recentReports(claims: ExportedClaim[], limit: number): Report[] {
  return claims
    .flatMap((claim) =>
      claim.articles.map((article) => ({
        claim,
        outlet: article.outlet,
        title: article.title,
        url: article.url,
        publishedDate: article.published_date,
      })),
    )
    .sort(
      (a, b) => b.publishedDate.localeCompare(a.publishedDate) || a.title.localeCompare(b.title),
    )
    .slice(0, limit);
}

/** How many of a claim's reports its page names under the title. */
export const FOLLOWED_SHOWN = 3;

/** A claim's own reports, in the order the home page lists reports. */
export function followedReports(claim: ExportedClaim): ExportedClaim["articles"] {
  return [...claim.articles].sort(
    (a, b) => b.published_date.localeCompare(a.published_date) || a.title.localeCompare(b.title),
  );
}

/** The name a headline has on the home page and on its claim page, so that the
 * browser carries it from one to the other. One name per page, so it is built
 * from the claim and the report's place in it. */
export function followedName(slug: string, index: number): string {
  return `r-${slug}-${index}`;
}

/** The name for one report of a claim, or null when its page does not show it. */
export function followedNameFor(claim: ExportedClaim, url: string): string | null {
  const index = followedReports(claim).findIndex((article) => article.url === url);
  return index >= 0 && index < FOLLOWED_SHOWN ? followedName(claim.slug, index) : null;
}
