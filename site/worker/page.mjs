// What a news page says about itself, beyond its visible text: the headline, summary and
// date in the tags it carries for other software, the article as structured data, and
// the papers and registry records it links to. Read from the page the site served and
// kept nowhere. The same rules as the pipeline's thenwhat.extract.page; keep the two in step.

const MAX_PAGE_CHARACTERS = 1_500_000;
// A body shorter than this is a teaser, not the article.
export const BODY_FROM = 500;
// The most papers and registry numbers one page is taken to report.
const MAX_LINKED = 5;
const ENTITIES = { nbsp: " ", amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
const HEADLINE_TAGS = ["og:title", "twitter:title"];
const SUMMARY_TAGS = ["og:description", "description", "twitter:description"];
const DATE_TAGS = ["article:published_time", "date", "dc.date", "pubdate", "parsely-pub-date"];
const STRUCTURED_FIELDS = ["headline", "description", "datePublished", "articleBody"];

const SKIPPED = /<(script|style|noscript|template|svg)\b[\s\S]*?<\/\1\s*>/gi;
const STRUCTURED = /<script\b[^>]*\btype\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script\s*>/gi;
const ATTRIBUTE = /([a-z][a-z0-9:_-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')/gi;
const REGISTRY_NUMBER = /NCT\d{8}/gi;
const DOI = String.raw`10\.\d{4,9}/[^\s?#&"'<>]+`;
// Where a link gives a paper's DOI: the resolver itself, or a publisher's own address.
const DOI_LINKS = [
  new RegExp(String.raw`doi\.org/(${DOI})`, "gi"),
  new RegExp(String.raw`/doi/(?:(?:full|abs|pdf|epdf|epub)/)?(${DOI})`, "gi"),
];
// Publishers whose article address holds the DOI's second half.
const NATURE = /nature\.com\/articles\/([a-z0-9][a-z0-9.-]+)/gi;
const ELSEVIER_PII = /(?:thelancet|cell)\.com\/[^\s"']*?\/PII(S[0-9X()-]+)/gi;
const PUBMED = /(?:pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov\/pubmed)\/(\d{4,9})/g;

const tidy = (text) => String(text).replace(/\s+/g, " ").trim();
const unique = (items) => [...new Set(items)].slice(0, MAX_LINKED);
const captured = (text, pattern) => [...text.matchAll(pattern)].map((match) => match[1]);

export function decoded(text) {
  return text
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&([a-z]+);/gi, (whole, name) => ENTITIES[name.toLowerCase()] ?? whole);
}

function attributes(tag) {
  return Object.fromEntries([...tag.matchAll(ATTRIBUTE)].map((found) => [found[1].toLowerCase(), decoded(found[2] ?? found[3])]));
}

/** The article's own fields, from the first structured-data object that has each. */
function structured(html) {
  const found = {};
  const walk = (node) => {
    if (Array.isArray(node)) return node.forEach(walk);
    if (!node || typeof node !== "object") return;
    for (const name of STRUCTURED_FIELDS) {
      if (typeof node[name] === "string" && node[name].trim() && !(name in found)) found[name] = tidy(node[name]);
    }
    Object.values(node).forEach(walk);
  };
  for (const block of captured(html, STRUCTURED)) {
    try {
      walk(JSON.parse(block));
    } catch {
      // A page's structured data is often malformed; the rest still counts.
    }
  }
  return found;
}

function unescaped(link) {
  try {
    return decodeURIComponent(link);
  } catch {
    return link;
  }
}

/**
 * @returns {{ text: string, headline: string | null, summary: string | null, published: string | null,
 *   body: string | null, registryNumbers: string[], dois: string[], pubmedIds: string[] }}
 */
export function readPage(html) {
  const source = String(html).slice(0, MAX_PAGE_CHARACTERS);
  const described = structured(source);
  const visible = source.replace(SKIPPED, " ").replace(/<!--[\s\S]*?-->/g, " ");

  const tags = {};
  for (const [tag] of visible.matchAll(/<meta\b[^>]*>/gi)) {
    const given = attributes(tag);
    const name = (given.property || given.name || "").toLowerCase();
    if (name && given.content && !(name in tags)) tags[name] = tidy(given.content);
  }
  const first = (names) => names.map((name) => tags[name]).find(Boolean) ?? null;
  const title = visible.match(/<title[^>]*>([\s\S]*?)<\/title\s*>/i);
  const links = [...visible.matchAll(/<a\b[^>]*>/gi)]
    .map(([tag]) => attributes(tag).href)
    .filter(Boolean)
    .map(unescaped)
    .join(" ");
  const allText = tidy(decoded(visible.replace(/<[^>]+>/g, " ")));
  const main = [...visible.matchAll(/<main\b[^>]*>([\s\S]*?)<\/main\s*>/gi)]
    .map((match) => match[1]).join(" ");
  const mainText = tidy(decoded(main.replace(/<[^>]+>/g, " ")));
  const text = mainText || allText;

  return {
    text,
    headline: first(HEADLINE_TAGS) ?? described.headline ?? (title ? tidy(decoded(title[1])) || null : null),
    summary: first(SUMMARY_TAGS) ?? described.description ?? null,
    published: first(DATE_TAGS) ?? described.datePublished ?? null,
    body: described.articleBody ?? null,
    ...linkSignals(links, allText),
  };
}

/**
 * The registry numbers in a text and its links, and the papers the links point to.
 * @param {string | string[]} links the addresses a page links to
 */
export function linkSignals(links, text = "") {
  const joined = Array.isArray(links) ? links.map(unescaped).join(" ") : links;
  const dois = [
    ...DOI_LINKS.flatMap((pattern) => captured(joined, pattern)).map((doi) => doi.replace(/[.,;]+$/, "")),
    ...captured(joined, NATURE).map((name) => `10.1038/${name}`),
    ...captured(joined, ELSEVIER_PII).map((pii) => `10.1016/${pii}`),
  ].map((doi) => doi.toLowerCase());
  return {
    registryNumbers: unique((`${text} ${joined}`.match(REGISTRY_NUMBER) ?? []).map((number) => number.toUpperCase())),
    dois: unique(dois),
    pubmedIds: unique(captured(joined, PUBMED)),
  };
}

/** The page for a reader who sees only text: what it is first, then the article. */
export function pageAsText(page) {
  const lead = [
    ["Headline", page.headline],
    ["Summary", page.summary],
    ["Published", page.published],
  ]
    .filter(([, value]) => value)
    .map(([label, value]) => `${label}: ${value}`)
    .join("\n");
  const body = page.body && page.body.length >= BODY_FROM ? page.body : page.text;
  return [lead, body].filter(Boolean).join("\n\n");
}
