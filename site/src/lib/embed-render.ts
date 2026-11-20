// A pair's embed and its oEmbed description, as the Worker makes them on request
// (worker/shares.mjs, openspec pairs-site task 4.6): the status, made to sit inside another
// site's frame, asking no other host for anything, its links opening in the whole window. Pure,
// so the frame the build leaves (src/pair/EmbedShell.astro) and the Worker agree on the markup.
// Every value from a page file goes through `escape`.
import { CARD_NOTICE, clip, monthAndYear } from "./card.ts";
import { escape, statusWords } from "./blocks.ts";
import type { PairView } from "./pair-view.ts";
import { EMBED_SIZE, embedSnippet } from "./share.ts";
import { formatDate } from "./timetable.ts";

/** The embed's title: the treatment and the condition. */
export const embedTitle = (view: PairView) => `${view.intervention} for ${view.condition.toLowerCase()}`;

/** The embed's body, above the frame's footer: the site's name, the status and when it was
 * checked. */
export function renderEmbedArticle(view: PairView, siteName: string, siteUrl: string): string {
  const page = `${siteUrl}/${view.address}`;
  return [
    `<p class="embed-name"><a href="${escape(page)}" target="_top">${escape(siteName)}</a> <span>${escape(CARD_NOTICE)}</span></p>`,
    `<h1>${escape(clip(embedTitle(view), 160))}</h1>`,
    `<div class="embed-status" data-pair-status="${escape(view.statusCode)}">${statusWords(view.status, view.gloss)}</div>`,
    `<p class="embed-more"><span>Checked ${escape(monthAndYear(view.asOf))}.</span> <a href="${escape(page)}" target="_top">Records and sources</a></p>`,
  ].join("");
}

/** When the registries were read, for the frame's footer line on data sources. */
export function renderEmbedRegistries(view: PairView): string {
  const latestCheck = view.registryChecks.map((check) => check.through).sort().at(-1) ?? null;
  return latestCheck
    ? ` Registries last checked ${escape(formatDate(latestCheck))}.`
    : ` Registries: status worked out ${escape(formatDate(view.asOf))} from the trial records.`;
}

/**
 * A pair's oEmbed description: how a site that turns pasted links into embeds finds the pair's
 * embed. Its picture is the site's own card (`card`, an absolute address): no pair has a
 * picture of its own, so no file is drawn per pair.
 */
export function oembedOf(view: PairView, siteName: string, siteUrl: string, card: string) {
  const title = embedTitle(view);
  return {
    version: "1.0",
    type: "rich",
    title,
    provider_name: siteName,
    provider_url: new URL("/", siteUrl).href,
    html: embedSnippet(siteUrl, view.address, title),
    width: EMBED_SIZE.width,
    height: EMBED_SIZE.height,
    thumbnail_url: card,
    thumbnail_width: 1200,
    thumbnail_height: 630,
    // A day: the registries are checked at most twice a day.
    cache_age: 86400,
  };
}
