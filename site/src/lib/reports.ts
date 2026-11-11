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
