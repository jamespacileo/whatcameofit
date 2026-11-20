// The building blocks pages are made of (openspec pairs-site, shared components): one source of
// markup and class names for the pages the Worker makes on request (lib/pair-render.ts,
// lib/listing-render.ts, lib/embed-render.ts) and the pages the build makes, which call the same
// functions through `<Fragment set:html>`. Plain functions of plain values, so the Worker and
// Astro write the same HTML; tests/goldens/ holds what they write for the fixture. Every value
// placed in the HTML goes through `escape`; a function given HTML says so in its parameter's name.

import { UNCHECKED_BYLINE } from "./notices.ts";
import { formatDate } from "./timetable.ts";

const ENTITIES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Text made safe to place in HTML, between tags or in a quoted attribute. */
export function escape(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ENTITIES[character]);
}

/**
 * The band at the head of a record page: navy, holding where the page sits, its title and what
 * it is (global.css, "record band"). `attributes` is the section's own, written as HTML after its
 * class (an aria-label, data attributes).
 */
export function band(attributes: string, html: string[]): string {
  return [`<section class="band record"${attributes}><div class="wrap band-grid"><div class="band-main">`, ...html, `</div></div></section>`].join("");
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

/** The sheet under a band: the page's content in the site's frame, with no section rail. */
export function sheet(html: string[]): string {
  return [`<div class="frame no-rail"><div class="sheet">`, ...html, `</div></div>`].join("");
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

/** A list of pairs as a table (pair/pair.css, "pair-table"): each pair's page, where it stands
 * and as of when, and its trials; `caption` names the list for a screen reader. */
export function pairTable(caption: string, rows: PairTableRow[]): string {
  if (rows.length === 0) return `<p>No pair is listed here yet.</p>`;
  return [
    `<table class="pair-table" data-pair-table><caption class="visually-hidden">${escape(caption)}</caption>`,
    `<thead><tr><th scope="col">Treatment and condition</th><th scope="col">Where it stands</th><th scope="col">Trials</th></tr></thead><tbody>`,
    ...rows.map(
      (row) =>
        `<tr data-pair="${escape(row.address)}"><th scope="row"><a href="/${escape(row.address)}">${escape(row.intervention)} for ${escape(row.condition.toLowerCase())}</a></th>` +
        `<td data-status="${escape(row.statusCode)}">${escape(row.status)}, as of ${escape(formatDate(row.asOf))}${row.checkedByPerson ? "" : ` <span class="note">(${escape(UNCHECKED_BYLINE[1])})</span>`}</td>` +
        `<td>${row.trials}</td></tr>`,
    ),
    `</tbody></table>`,
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
