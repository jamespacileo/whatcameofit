// Addresses that are gone. Until 2026-11-20 the site tracked claims; the operator removed
// them, and before that archived some. Each such address answers 410 with a short note, so
// readers and search engines learn it was removed on purpose. The build writes the list to
// /gone.json (scripts/redirects.mjs). The reason is never published.
// Behaviour: openspec site-publishing "Archived addresses answer gone".
//
// The same list carries the addresses that lead somewhere: a claim that one published pair
// came from answers with a permanent redirect to that pair (`to`).

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** "2026-11-14" as "14 November 2026". */
export function spokenDate(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/** The note shown at an address that is gone: with the day, where the operator archived it. */
export function gonePage(on, siteName) {
  const said = on ? `This page was taken down on ${spokenDate(on)}.` : "This page has been removed.";
  return `<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Page removed · ${siteName}</title>
<style>
:root { color-scheme: light; }
body { margin: 0; background: #ffffff; color: #0f1f38; font: 400 1.0625rem/1.55 "Helvetica Neue", Arial, sans-serif; }
main { max-width: 36rem; margin: 0 auto; padding: 4rem 1rem; }
h1 { margin: 0 0 0.75rem; font-size: 1.75rem; line-height: 1.2; text-wrap: balance; }
a { color: #14427f; text-underline-offset: 2px; }
</style>
</head>
<body>
<main>
<h1>${said}</h1>
<p><a href="/">Search what ${siteName} follows</a></p>
</main>
</body>
</html>
`;
}

let cached = null;

/** Slug to its entry for every address that is gone (`on`, the day it was archived, or
 *  `gone`) and every address that leads to a pair (`to`), read once per Worker instance. */
export async function goneList(assets, origin) {
  if (cached) return cached;
  const response = await assets.fetch(new Request(new URL("/gone.json", origin))).catch(() => null);
  const list = response?.ok ? await response.json().catch(() => []) : [];
  cached = new Map(list.map((entry) => [entry.slug, entry]));
  return cached;
}

/** For tests: forget the list read so far. */
export function forgetGoneList() {
  cached = null;
}
