// An Atom feed of the anniversaries of the last thirty days. Each item is dated to its
// anniversary, never to the build, and states the years passed as of that date.
import type { APIRoute } from "astro";
import { SITE } from "../../site.config.mjs";
import { recentAnniversaries } from "../lib/anniversaries";
import { data } from "../lib/export";
import { STATUS_LABELS } from "../lib/status";
import { formatDate } from "../lib/timetable";

const escape = (text: string) =>
  text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

export const GET: APIRoute = () => {
  const items = recentAnniversaries(data.claims, data.generated_at);
  const feedUpdated = `${items[0]?.date ?? data.generated_at.slice(0, 10)}T00:00:00Z`;

  const entries = items.map(({ date, years, claim }) => {
    const link = `${SITE.url}/${claim.slug}`;
    const summary =
      `First reported ${formatDate(claim.first_reported_date)}. ` +
      `${years} ${years === 1 ? "year" : "years"} on: ${STATUS_LABELS[claim.status.code]}.`;
    return [
      "  <entry>",
      `    <title>${escape(claim.headline)}</title>`,
      `    <id>${escape(`${link}#anniversary-${date}`)}</id>`,
      `    <link href="${escape(link)}"/>`,
      `    <updated>${date}T00:00:00Z</updated>`,
      `    <summary>${escape(summary)}</summary>`,
      "  </entry>",
    ].join("\n");
  });

  const xml = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    `  <title>${escape(`${SITE.name} Anniversaries`)}</title>`,
    `  <id>${escape(`${SITE.url}/anniversaries.xml`)}</id>`,
    `  <link rel="self" href="${escape(`${SITE.url}/anniversaries.xml`)}"/>`,
    `  <link href="${escape(`${SITE.url}/anniversaries`)}"/>`,
    `  <updated>${feedUpdated}</updated>`,
    ...entries,
    "</feed>",
    "",
  ].join("\n");

  return new Response(xml, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
