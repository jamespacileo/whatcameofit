// The building blocks pages are made of (openspec pairs-site, shared components): one source of
// markup and class names for the pages the Worker makes on request (lib/pair-render.ts,
// lib/listing-render.ts, lib/embed-render.ts) and the pages the build makes, which call the same
// functions through `<Fragment set:html>`. Plain functions of plain values, so the Worker and
// Astro write the same HTML; tests/goldens/ holds what they write for the fixture. Every value
// placed in the HTML goes through `escape`; a function given HTML says so in its parameter's name.

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
