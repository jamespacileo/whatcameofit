// A listing page's content as HTML: one renderer for a listing built ahead and one the Worker
// makes on request (worker/listings.mjs), so the two are the same for the same file. Every value
// from a page file goes through `escape`. It fills the same frame as a pair page (/pair-shell).
import type { ListingView } from "./listing-view.ts";
import { escape } from "./pair-render.ts";
import { renderCard } from "./card-render.ts";
import { breadcrumbData } from "./structured.ts";
import { UNCHECKED_BYLINE } from "./notices.ts";
import { formatDate } from "./timetable.ts";

const count = (n: number) => (n === 1 ? "1 treatment and condition" : `${n} treatments and conditions`);

/** The trail above the page as structured data, as `Base` writes it for a built page. "<" is
 * escaped so that no text can close the script element. */
function trailData(view: ListingView): string {
  const trail = [...view.crumbs.map((crumb) => ({ name: crumb.label, path: crumb.href })), { name: view.title, path: view.path }];
  return `<script type="application/ld+json">${JSON.stringify(breadcrumbData(trail)).replace(/</g, "\\u003c")}</script>`;
}

/** The credit NLM's terms ask for wherever a MeSH category is shown, in the words of
 * components/MeshCredit.astro: a test holds the two the same. `edition` is the vocabulary's
 * year as the build states it. */
export function renderMeshCredit(edition: string): string {
  return (
    `<p class="mesh-credit" data-pagefind-ignore>Categories are from Medical Subject Headings (MeSH), U.S. National Library of Medicine, ` +
    `courtesy of the U.S. National Library of Medicine: ${escape(edition)}. They may not reflect the most current data available from NLM. NLM does not endorse this site.</p>`
  );
}

/** The band: where the page sits, its title, and what it is. */
export function renderListingBand(view: ListingView): string {
  return [
    trailData(view),
    `<section class="band record" aria-label="${escape(view.title)}"><div class="wrap band-grid"><div class="band-main">`,
    view.crumbs.length
      ? `<nav class="crumbs" aria-label="Where this page sits">${view.crumbs.map((crumb) => `<a href="${escape(crumb.href)}">${escape(crumb.label)}</a>`).join(" · ")}</nav>`
      : "",
    `<h1 class="title" data-listing="${escape(view.kind)}">${escape(view.title)}</h1>`,
    `<p class="lede" data-pagefind-ignore>${escape(count(view.rows.length))} followed through the public trial records. Not medical advice. <a href="/how-it-works">How a status is set</a></p>`,
    view.card ? renderCard(view.card) : "",
    `</div></div></section>`,
  ].join("");
}

/** The sheet: the notes, the linked categories, then the list, and on a category's page the
 * vocabulary's credit (`meshEdition`, the year the build states). */
export function renderListingSheet(view: ListingView, meshEdition: string): string {
  return [
    `<div class="frame no-rail"><div class="sheet">`,
    ...view.notes.map((note) => `<p class="what-this-is">${escape(note)}</p>`),
    ...view.linkGroups.map(
      (group) =>
        `<p data-links="${escape(group.label.toLowerCase())}">${escape(group.label)}: ${group.links
          .map((link) => `<a href="${escape(link.href)}">${escape(link.label)}</a>${link.count === undefined ? "" : ` <span class="count">${link.count}</span>`}`)
          .join(", ")}</p>`,
    ),
    `<h2 class="bar sheet-title" id="pairs">Treatments and conditions</h2>`,
    view.rows.length === 0
      ? `<p>No pair is listed here yet.</p>`
      : [
          `<table class="pair-table" data-pair-table><caption class="visually-hidden">${escape(view.title)}</caption>`,
          `<thead><tr><th scope="col">Treatment and condition</th><th scope="col">Where it stands</th><th scope="col">Trials</th></tr></thead><tbody>`,
          ...view.rows.map(
            (row) =>
              `<tr data-pair="${escape(row.address)}"><th scope="row"><a href="/${escape(row.address)}">${escape(row.intervention)} for ${escape(row.condition.toLowerCase())}</a></th>` +
              `<td data-status="${escape(row.statusCode)}">${escape(row.status)}, as of ${escape(formatDate(row.asOf))}${row.checkedByPerson ? "" : ` <span class="note">(${escape(UNCHECKED_BYLINE[1])})</span>`}</td>` +
              `<td>${row.trials}</td></tr>`,
          ),
          `</tbody></table>`,
        ].join(""),
    view.kind === "category" ? renderMeshCredit(meshEdition) : "",
    `</div></div>`,
  ].join("");
}
