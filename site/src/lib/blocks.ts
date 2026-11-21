// The building blocks pages are made of (openspec pairs-site, shared components): one source of
// markup and class names for the pages the Worker makes on request (lib/pair-render.ts,
// lib/listing-render.ts, lib/embed-render.ts) and the pages the build makes, which call the same
// functions through `<Fragment set:html>`. Plain functions of plain values, so the Worker and
// Astro write the same HTML; tests/goldens/ holds what they write for the fixture. Every value
// placed in the HTML goes through `escape`; a function given HTML says so in its parameter's name.

import { UNCHECKED_BYLINE } from "./notices.ts";
import { OFF_PATH, STAGE_PATH, STATUS_GLOSSES, STATUS_LABELS, statusCounts } from "./status.ts";
import { formatDate } from "./timetable.ts";

const ENTITIES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Text made safe to place in HTML, between tags or in a quoted attribute. */
export function escape(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ENTITIES[character]);
}

/**
 * The band at the head of a record page: navy, holding where the page sits, its title and what
 * it is (global.css, "record band"). `attributes` is the section's own, written as HTML after its
 * class (an aria-label, data attributes). `sideHtml` is the card at the band's right, level with
 * the title (a pair's "Where it stands"); under the title on a narrow screen.
 */
export function band(attributes: string, html: string[], sideHtml = ""): string {
  return [`<section class="band record"${attributes}><div class="wrap band-grid"><div class="band-main">`, ...html, `</div>`, sideHtml, `</div></section>`].join("");
}

export interface Crumb {
  href: string;
  label: string;
  /** A data attribute the link carries, by name (as `data-pair-intervention`), with no value. */
  data?: string;
}

/** Where a page sits: its links, joined by a middle dot, under the given label. */
export function crumbs(label: string, links: Crumb[]): string {
  return `<nav class="crumbs" aria-label="${escape(label)}">${links
    .map((link) => `<a href="${escape(link.href)}"${link.data ? ` ${link.data}` : ""}>${escape(link.label)}</a>`)
    .join(" · ")}</nav>`;
}

/** The page's title, in the band. `data` is an attribute written as HTML after its class. */
export const bandTitle = (title: string, data = "") => `<h1 class="title"${data}>${escape(title)}</h1>`;

/**
 * What a record page is, in one line: `subject` (HTML, as "A treatment and a condition,") is
 * followed through the public trial records, which is not medical advice, with the way to how a
 * status is set. `className` is the line's place in its band.
 */
export function followedLine(subjectHtml: string, className: string): string {
  return `<p class="${className}" data-pagefind-ignore>${subjectHtml} followed through the public trial records. Not medical advice. <a href="/how-it-works">How a status is set</a></p>`;
}

/** A status and its gloss, as a sentence: the status in bold, never coloured. */
export const statusWords = (status: string, gloss: string) => `<strong>${escape(status)}</strong>. ${escape(gloss)}.`;

/** The sheet under a band: the page's content in the site's frame. With `railHtml` (a
 * `sectionList`) the frame keeps its first column for it; with none it has no section rail. */
export function sheet(html: string[], railHtml = ""): string {
  return [railHtml ? `<div class="frame">${railHtml}<div class="sheet">` : `<div class="frame no-rail"><div class="sheet">`, ...html, `</div></div>`].join("");
}

/** A heading of the sheet, with the address of its place on the page. */
export const sheetHeading = (text: string, id: string) => `<h2 class="bar sheet-title" id="${escape(id)}">${escape(text)}</h2>`;

/** A dated list of what happened, oldest first as given. `attributes` is the list's own, as HTML. */
export function eventList(attributes: string, itemsHtml: string[]): string {
  return [`<ol class="pair-events"${attributes}>`, ...itemsHtml, `</ol>`].join("");
}

/** One pair in a list of pairs: where it stands and how many trials it is followed through. */
export interface PairTableRow {
  address: string;
  intervention: string;
  condition: string;
  statusCode: string;
  status: string;
  asOf: string;
  checkedByPerson: boolean;
  trials: number;
}

/** How many pairs a list holds before it has a stage filter: six, as the claims site's tables
 * had (DESIGN.md, "Stage filter"). A shorter list is read at a glance. */
export const STAGE_FILTER_FROM = 6;

/**
 * The path as a filter (DESIGN.md, "Stage filter"; the claims site's StageFilter, recovered for
 * pairs): how many of a list's pairs stand at each place, each count a button that narrows the
 * table after it to that place, and a box that narrows it by a word. It doubles as the key to
 * the small tracks in the table's rows. scripts/pair-filter.ts does the narrowing; with no
 * script the counts still read as a summary. A place with no pair is disabled. Nothing here
 * is coloured by status.
 */
export function stageFilter(rows: { statusCode: string }[]): string {
  if (rows.length < STAGE_FILTER_FROM) return "";
  const counts = statusCounts(rows);
  const place = (code: string, off: boolean) => {
    const count = counts.get(code) ?? 0;
    const label = STATUS_LABELS[code as keyof typeof STATUS_LABELS];
    return (
      `<button type="button" class="${off ? "place off" : "place"}" data-status="${escape(code)}" data-label="${escape(label)}" aria-pressed="false"${count === 0 ? " disabled" : ""}>` +
      `${off ? "" : `<span class="dot" aria-hidden="true"></span>`}<strong>${count}</strong><span class="place-name">${escape(label)}</span></button>`
    );
  };
  const offPath = OFF_PATH.filter((code) => counts.has(code));
  return [
    `<div class="stage-filter" data-stage-filter data-pagefind-ignore>`,
    `<label class="word-field"><span class="visually-hidden">Filter this list by a word</span><input type="search" placeholder="Find a treatment or condition" autocomplete="off" data-words></label>`,
    `<div class="places" role="group" aria-label="Show only the pairs at one status">`,
    ...STAGE_PATH.map((code) => place(code, false)),
    `</div>`,
    offPath.length ? `<div class="off-path" role="group" aria-label="Statuses off the path">${offPath.map((code) => place(code, true)).join("")}</div>` : "",
    `<p class="shown" hidden data-shown><span aria-live="polite" data-shown-text></span> <button type="button" data-show-all>Show all</button></p>`,
    `<div class="no-match" hidden data-none><p><strong>Nothing here matches.</strong> <span data-none-what></span></p><button type="button" class="share" data-show-all>Show all ${rows.length}</button></div>`,
    `</div>`,
  ].join("");
}

/** A status in a row of a list: its place on the path, its label and the same in plain words
 * (the claims site's StatusCell). The track is the path's shape only, never coloured by status. */
export function statusCell(code: string, status: string): string {
  const gloss = STATUS_GLOSSES[code as keyof typeof STATUS_GLOSSES];
  return `<span class="status-line">${stageTrack(code, { off: true })}<strong class="status-name">${escape(status)}</strong></span>${gloss ? `<span class="gloss">${escape(gloss)}</span>` : ""}`;
}

/** The one value every row shares, or null when they differ (or there are none). */
const shared = <T,>(values: T[]): T | null => (values.length > 0 && values.every((value) => value === values[0]) ? values[0] : null);

/** A list of pairs as a table (pair/pair.css, "pair-table"): each pair's page, where it stands
 * on the path and in words, and its trials; `caption` names the list for a screen reader.
 * The day the statuses are as of, and that no person has checked a page yet, are said once
 * above the table when every row shares them, and in the row only when rows differ: on the
 * rehearsal bundle every row of every list repeated the same two notes. */
export function pairTable(caption: string, rows: PairTableRow[]): string {
  if (rows.length === 0) return `<p>No pair is listed here yet.</p>`;
  const asOf = shared(rows.map((row) => row.asOf));
  const unchecked = shared(rows.map((row) => row.checkedByPerson)) === false;
  const said = [asOf ? `Statuses as of ${escape(formatDate(asOf))}.` : "", unchecked ? `${escape(UNCHECKED_BYLINE[0])} ${escape(UNCHECKED_BYLINE[1])}.` : ""].filter(Boolean);
  return [
    said.length ? `<p class="note pair-table-note" data-pair-table-note>${said.join(" ")}</p>` : "",
    `<div class="table-frame"><table class="index pair-table" data-pair-table><caption class="visually-hidden">${escape(caption)}</caption>`,
    `<thead><tr><th scope="col">Treatment and condition</th><th scope="col">Where it stands</th><th scope="col" class="trials">Trials</th></tr></thead><tbody>`,
    ...rows.map(
      (row) =>
        `<tr data-pair="${escape(row.address)}" data-status="${escape(row.statusCode)}"><th scope="row" class="claim"><a href="/${escape(row.address)}">${escape(row.intervention)} for ${escape(row.condition.toLowerCase())}</a></th>` +
        `<td class="status" data-label="Where it stands">${statusCell(row.statusCode, row.status)}` +
        `${asOf ? "" : `<span class="gloss">As of ${escape(formatDate(row.asOf))}</span>`}` +
        `${unchecked || row.checkedByPerson ? "" : `<span class="gloss">${escape(UNCHECKED_BYLINE[1])}</span>`}</td>` +
        `<td class="trials" data-label="Trials">${row.trials}</td></tr>`,
    ),
    `</tbody></table></div>`,
  ].join("");
}

/** The credit NLM's terms ask for wherever a MeSH category is shown: the source by name, the
 * year of the vocabulary (`edition`, as the build states it) and that NLM does not endorse the
 * site (docs/sources.md; openspec site-publishing, "Clinical pages credit the vocabulary"). */
export function meshCredit(edition: string): string {
  return (
    `<p class="mesh-credit" data-pagefind-ignore>Categories are from Medical Subject Headings (MeSH), U.S. National Library of Medicine, ` +
    `courtesy of the U.S. National Library of Medicine: ${escape(edition)}. They may not reflect the most current data available from NLM. NLM does not endorse this site.</p>`
  );
}

/** The sources the pair pages' records come from, by name, for a line that cannot link them. */
export const sourceNames = (sources: { name: string }[]) => sources.map((source) => source.name).join(", ");

/** An embed's footer: the notices every page carries, then the data sources by name with
 * `registriesHtml` (when the registries were read) after them. The embed's frame
 * (pair/EmbedShell.astro) and the styleguide write it alike. */
export function embedFooter(notices: readonly string[], sources: { name: string }[], registriesHtml: string): string {
  return `<footer>${notices.map((notice) => `<p>${escape(notice)}</p>`).join("")}<p>Data sources: ${escape(sourceNames(sources))}.${registriesHtml}</p></footer>`;
}

// Short enough to sit under a dot; the full labels are STATUS_LABELS.
const PLACE_NAMES: Record<string, string> = {
  preclinical_only: "Pre\u00adclinical",
  trial_registered: "Regis\u00adtered",
  phase_1: "Phase 1",
  phase_2: "Phase 2",
  phase_3: "Phase 3",
  approved: "Approved",
};

/**
 * Where a status sits on the path from laboratory to approval (DESIGN.md, "Stage track"): six
 * places, one marked. It shows a position, not progress: a pair can reach a place without
 * passing the others, and the track is never filled up to its dot. It always sits beside the
 * status in words, and is never coloured by the status.
 * - `ends`: the place in words under the dots, the same words a screen reader is given;
 * - `named`: each place named under its dot, as in a panel that has room to say them;
 * - `off`: for a status off the path, a square alone, no path.
 */
export function stageTrack(code: string, { ends = false, named = false, off = false }: { ends?: boolean; named?: boolean; off?: boolean } = {}): string {
  const place = (STAGE_PATH as readonly string[]).indexOf(code);
  const name = `Place ${place + 1} of ${STAGE_PATH.length} on the path from preclinical to approved`;
  if (place >= 0 && named) {
    return `<span class="track named" role="img" aria-label="${escape(name)}">${STAGE_PATH.map(
      (stage, index) => `<span class="${index === place ? "place here" : "place"}">${escape(PLACE_NAMES[stage])}</span>`,
    ).join("")}</span>`;
  }
  if (place >= 0) {
    return [
      `<span class="${ends ? "track ends" : "track"}">`,
      `<span class="steps" role="img" aria-label="${escape(name)}">`,
      ...STAGE_PATH.map((_, index) => `<span class="${index === place ? "step here" : "step"}"></span>`),
      `</span>`,
      ends ? `<span class="ends" aria-hidden="true">Place ${place + 1} of ${STAGE_PATH.length}, from preclinical to approved</span>` : "",
      `</span>`,
    ].join("");
  }
  if (off && !named) return `<span class="track off" role="img" aria-label="Not a place on the path from preclinical to approved"><span class="off-mark"></span></span>`;
  return "";
}

/** Marks a record a status rests on (DESIGN.md, "Key"): a blue diamond, like the status label it
 * explains, said in words to a screen reader unless `label` is false. */
export function basisMark(label = true): string {
  return `<span class="basis-mark"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M6 0.6 11.4 6 6 11.4 0.6 6z"></path></svg>${label ? `<span class="visually-hidden">basis of status</span>` : ""}</span>`;
}

/**
 * Where a pair stands, as the card at the right of its band (DESIGN.md, "Digest panel"; the
 * claim page's "Where it stands" card, recovered for pairs): the status as the card's largest
 * words, the same in plain words, its place on the path said under the track, then each of
 * `linesHtml` as a quiet row (the latest record, the trials counted, when the status was set).
 * The label is blue as every status label is, never a colour of its status; a status off the
 * path has the square alone. `attributes` is the label's own, as HTML.
 */
export function standingCard(code: string, status: string, gloss: string, linesHtml: string[], attributes = ""): string {
  return [
    `<div class="digest" data-standing-card><h2 class="card-tab">Where it stands</h2><div class="standing">`,
    `<div class="label-row"><span class="label"${attributes}>${escape(status)}</span></div>`,
    `<p class="gloss">${escape(gloss)}</p>`,
    stageTrack(code, { ends: true, off: true }),
    ...linesHtml.filter(Boolean).map((line) => `<p class="changed" data-pagefind-ignore>${line}</p>`),
    `</div></div>`,
  ].join("");
}

export interface SectionItem {
  /** A section of this page, by its id. */
  id: string;
  name: string;
  /** What the section holds, counted, when that helps a reader choose ("4 trials"). */
  count?: string | number | null;
}

/**
 * The sections of a page, by name, with what each holds (DESIGN.md, "Section list"; the claim
 * pages' section rail, recovered): beside the sheet on a wide screen, one row of chips that
 * stays at the top on a narrow one. scripts/section-list.ts marks the section in view; with no
 * script it is a plain list of links. It takes the frame's first column, so a page that shows
 * it is framed with a rail (`<div class="frame">`, not `no-rail`).
 */
export function sectionList(label: string, items: SectionItem[]): string {
  return [
    `<nav class="onpage" aria-label="${escape(label)}" data-pagefind-ignore>`,
    `<p class="onpage-title" aria-hidden="true">${escape(label)}</p><ul class="onpage-list">`,
    ...items.map(
      (item) =>
        `<li><a href="#${escape(encodeURIComponent(item.id))}"><span>${escape(item.name)}</span>${item.count != null && item.count !== "" ? `<span class="n">${escape(item.count)}</span>` : ""}</a></li>`,
    ),
    `</ul></nav>`,
  ].join("");
}
