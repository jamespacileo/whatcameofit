// A listing page's content as HTML: one renderer for a listing built ahead and one the Worker
// makes on request (worker/listings.mjs), so the two are the same for the same file. Every value
// from a page file goes through `escape`. It fills the same frame as a pair page (/pair-shell).
import type { ListingView } from "./listing-view.ts";
import { band, bandTitle, crumbs, escape, followedLine, meshCredit, pageActions, pairTable, sheet, sheetHeading, stageFilter } from "./blocks.ts";
import { topicSentence } from "./share.ts";
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

/** What "Copy sentence" copies on a listing, before the page's address: the page's name, where
 * its pairs stand (the summary the band shows) and the month of the latest status among them.
 * Null where the band has no summary: one pair's sentence is on its own page. */
export function listingSentence(view: ListingView): string | null {
  const summary = view.rows.length > 1 ? standingSummary(statusCounts(view.rows)) : null;
  if (!summary) return null;
  const latest = view.rows.map((row) => row.asOf).sort().at(-1) ?? null;
  return topicSentence(`${view.title.replace(/[.\s]+$/, "")}. ${summary}`, latest, "").trim();
}

/** The band: where the page sits, its title, what it is, and the pills that pass it on. */
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
      pageActions(listingSentence(view)),
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
