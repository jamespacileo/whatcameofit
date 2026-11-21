// A listing page's content as HTML: one renderer for a listing built ahead and one the Worker
// makes on request (worker/listings.mjs), so the two are the same for the same file. Every value
// from a page file goes through `escape`. It fills the same frame as a pair page (/pair-shell).
import type { ListingView } from "./listing-view.ts";
import { band, bandTitle, crumbs, escape, followedLine, meshCredit, pairTable, sheet, sheetHeading, stageFilter } from "./blocks.ts";
import { standingSummary, statusCounts } from "./status.ts";
import { renderCard } from "./card-render.ts";
import { breadcrumbData } from "./structured.ts";

const count = (n: number) => (n === 1 ? "1 treatment and condition" : `${n} treatments and conditions`);

/** The trail above the page as structured data, as `Base` writes it for a built page. "<" is
 * escaped so that no text can close the script element. */
function trailData(view: ListingView): string {
  const trail = [...view.crumbs.map((crumb) => ({ name: crumb.label, path: crumb.href })), { name: view.title, path: view.path }];
  return `<script type="application/ld+json">${JSON.stringify(breadcrumbData(trail)).replace(/</g, "\\u003c")}</script>`;
}

/** The credit NLM's terms ask for, as lib/blocks.ts writes it for every page that shows a
 * category. */
export const renderMeshCredit = meshCredit;

/** The band: where the page sits, its title, and what it is. */
export function renderListingBand(view: ListingView): string {
  return (
    trailData(view) +
    band(` aria-label="${escape(view.title)}"`, [
      view.crumbs.length ? crumbs("Where this page sits", view.crumbs) : "",
      bandTitle(view.title, ` data-listing="${escape(view.kind)}"`),
      followedLine(escape(count(view.rows.length)), "what-this-is"),
      // Where the list's pairs stand, said once in plain words before the list (the claims
      // site's topic summary). One pair's status is in its row, so it is not said twice.
      view.rows.length > 1 ? `<p class="lede" data-listing-summary>${escape(standingSummary(statusCounts(view.rows)))}</p>` : "",
      view.card ? renderCard(view.card) : "",
    ])
  );
}

/** The sheet: the notes, the linked categories, then the list, and on a category's page the
 * vocabulary's credit (`meshEdition`, the year the build states). */
export function renderListingSheet(view: ListingView, meshEdition: string): string {
  return sheet([
    ...view.notes.map((note) => `<p class="what-this-is">${escape(note)}</p>`),
    ...view.linkGroups.map(
      (group) =>
        `<p data-links="${escape(group.label.toLowerCase())}">${escape(group.label)}: ${group.links
          .map((link) => `<a href="${escape(link.href)}">${escape(link.label)}</a>${link.count === undefined ? "" : ` <span class="count">${link.count}</span>`}`)
          .join(", ")}</p>`,
    ),
    sheetHeading("Treatments and conditions", "pairs"),
    stageFilter(view.rows),
    pairTable(view.title, view.rows),
    view.kind === "category" ? renderMeshCredit(meshEdition) : "",
  ]);
}
